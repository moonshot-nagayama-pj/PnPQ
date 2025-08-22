import threading
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from queue import Empty, Queue, SimpleQueue
from types import TracebackType
from typing import Callable, Iterator, Optional, Self

import serial.tools.list_ports
import structlog
from serial import Serial
from serial.tools.list_ports_common import ListPortInfo

import pnpq.apt
from pnpq.errors import InvalidStateException

from ..devices.utils import timeout
from ..events import Event
from .protocol import (
    Address,
    AptMessage,
    AptMessage_MGMSG_HW_REQ_INFO,
    AptMessage_MGMSG_HW_STOP_UPDATEMSGS,
    AptMessageForStreamParsing,
    AptMessageId,
)


class AbstractAptConnection(ABC):
    @abstractmethod
    def __enter__(self) -> "AbstractAptConnection":
        pass

    @abstractmethod
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        pass

    @abstractmethod
    def open(self) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def is_closed(self) -> bool:
        pass

    @abstractmethod
    def send_message_unordered(self, message: AptMessage) -> None:
        """Send a message as soon as the connection lock will allow,
        bypassing the message queue. This allows us to poll for status
        messages while the main message thread is blocked waiting for
        a reply.

        :param message: The message to send.
        """

    @abstractmethod
    def send_message_no_reply(self, message: AptMessage) -> None:
        """Send a message and return immediately, without waiting for
        any reply.

        :param message: The message to send.
        """

    @abstractmethod
    def send_message_expect_reply(
        self,
        message: AptMessage,
        match_reply: Callable[
            [
                AptMessage,
            ],
            bool,
        ],
    ) -> AptMessage:
        """Send a message and block until an expected reply is
        received.

        :param message: The message to send.

        :param match_reply: A function that returns ``True`` if a received message should be recognized as a reply to the sent message, and ``False`` otherwise.

        :return: The first message to match ``match_reply``'s test.

        """

    @abstractmethod
    @contextmanager
    def subscribe(self) -> Iterator[Queue[AptMessage]]:
        """Subscribe to all messages received from the device. This
        can be used to, for example, implement custom logging.

        :yield: A queue which receives all messages received by the device.

        """


@dataclass(frozen=True, kw_only=True)
class SerialConfig:
    """Serial connection configuration parameters, to be passed to
    ``serial.Serial``. These defaults are used by all known Thorlabs
    devices that implement the APT protocol and should not need to be
    changed."""

    baudrate: int = field(default=115200)
    bytesize: int = field(default=serial.EIGHTBITS)
    exclusive: bool = field(default=True)
    parity: str = field(default=serial.PARITY_NONE)
    rtscts: bool = field(default=True)
    stopbits: int = field(default=serial.STOPBITS_ONE)
    timeout: None | float = field(default=1.0)
    write_timeout: None | float = field(default=1.0)


class _OrderedSenderQueueItem(ABC):
    """Abstract base class for items to be enqueued for sending by the
    ordered sender."""


@dataclass(frozen=True, kw_only=True)
class _OrderedSenderQueueItemNoReply(_OrderedSenderQueueItem):
    message: AptMessage = field()


@dataclass(frozen=True, kw_only=True)
class _OrderedSenderQueueItemExpectReply(_OrderedSenderQueueItem):
    message: AptMessage = field()

    match_reply: Callable[
        [
            AptMessage,
        ],
        bool,
    ] = field()
    """The provided ``Callable`` will be executed on all incoming
    messages until it matches one, returning ``True``. The matching
    message will be forwarded to the provided ``reply_queue``."""

    reply_queue: Queue[AptMessage] = field()
    """Queue that the requesting function can listen on for a matching
    reply."""


@dataclass(frozen=True, kw_only=True)
class AptConnection(AbstractAptConnection):
    # Required

    serial_number: str = field()

    # Optional

    # Serial connection parameters. These defaults are used by all
    # known Thorlabs devices that implement the APT protocol and do
    # not need to be changed.
    serial_config: SerialConfig = field(default_factory=SerialConfig)

    # Private member variables

    _connection: Serial = field(init=False)

    _rx_lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _rx_dispatcher_thread: threading.Thread = field(init=False)
    _rx_dispatcher_subscribers: dict[int, Queue[AptMessage]] = field(
        default_factory=dict,
        init=False,
    )
    _rx_dispatcher_subscribers_lock: threading.Lock = field(
        default_factory=threading.Lock,
        init=False,
    )

    _tx_lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _tx_ordered_sender_thread: threading.Thread = field(init=False)
    _tx_ordered_sender_queue: Queue[_OrderedSenderQueueItem] = field(
        default_factory=Queue, init=False
    )

    _open_close_lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _opened_event: threading.Event = field(default_factory=threading.Event, init=False)
    _closed_event: threading.Event = field(default_factory=threading.Event, init=False)
    _close_exception_queue: SimpleQueue[BaseException] = field(
        default_factory=SimpleQueue, init=False
    )

    # Class variables

    log = structlog.get_logger()

    # Public API

    def __enter__(self) -> Self:
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._close(e=exc_val)

    def open(self) -> None:
        with self._open_close_lock:
            self._open()

    def close(self) -> None:
        self._close()

    def is_closed(self) -> bool:
        return not self._opened_event.is_set()

    def send_message_unordered(self, message: AptMessage) -> None:
        """Send a message as soon as the serial connection lock will
        allow, bypassing the message queue. This allows us to poll for
        status messages while the main message thread is blocked
        waiting for a reply.

        """
        self._fail_if_closed()
        self._send_message_unordered(message)

    def send_message_no_reply(self, message: AptMessage) -> None:
        """Send a message and return immediately, without waiting for any reply."""
        self._fail_if_closed()
        self._tx_ordered_sender_queue.put(
            _OrderedSenderQueueItemNoReply(message=message)
        )

    def send_message_expect_reply(
        self,
        message: AptMessage,
        match_reply: Callable[
            [
                AptMessage,
            ],
            bool,
        ],
    ) -> AptMessage:
        self._fail_if_closed()
        reply_queue: Queue[AptMessage] = Queue()
        self._tx_ordered_sender_queue.put(
            _OrderedSenderQueueItemExpectReply(
                message=message, match_reply=match_reply, reply_queue=reply_queue
            )
        )
        reply = reply_queue.get()
        reply_queue.task_done()
        return reply

    @contextmanager
    def subscribe(self) -> Iterator[Queue[AptMessage]]:
        """Subscribe to all messages received from the device. This
        can be used to, for example, implement custom logging."""
        self._fail_if_closed()
        queue: Queue[AptMessage] = Queue()
        object_id = id(queue)
        with self._rx_dispatcher_subscribers_lock:
            self._rx_dispatcher_subscribers[object_id] = queue
        try:
            yield queue
        finally:
            with self._rx_dispatcher_subscribers_lock:
                self._rx_dispatcher_subscribers.pop(object_id)

    # Utility functions

    def _clean_buffer(self) -> None:
        self._send_message_unordered(
            AptMessage_MGMSG_HW_STOP_UPDATEMSGS(
                destination=Address.GENERIC_USB,
                source=Address.HOST_CONTROLLER,
            )
        )
        time.sleep(0.5)
        self._connection.flush()
        time.sleep(0.5)
        self._connection.reset_input_buffer()
        self._connection.reset_output_buffer()

    def _fail_if_closed(self) -> bool:
        if self.is_closed():
            raise InvalidStateException("Tried to use a closed AptConnection object.")
        return True

    def _find_port(self) -> ListPortInfo:
        port_found = False
        port = None
        for possible_port in serial.tools.list_ports.comports():
            if possible_port.serial_number == self.serial_number:
                port = possible_port
                port_found = True
                break
        if not port_found:
            raise ValueError(
                f"Serial number {self.serial_number} could not be found, failing intialization."
            )
        assert port is not None
        return port

    def _send_message_unordered(self, message: AptMessage) -> None:
        # Private implementation of send message unordered without the _fail_if_closed() check.
        # Used for flushing buffer once the connection is closed.
        with self._tx_lock:
            self.log.debug(event=Event.TX_MESSAGE_UNORDERED, message=message)
            self._connection.write(message.to_bytes())

    # Open / close implementations

    def _open(self) -> None:
        if self._opened_event.is_set():
            raise InvalidStateException(
                "Tried to re-open a connection that was already open."
            )
        if self._closed_event.is_set():
            raise InvalidStateException(
                "Tried to re-open a connection that was already closed."
            )

        # These devices tend to take a few seconds to start up, and
        # this library tends to be used as part of services that start
        # automatically on computer boot. For safety, wait here before
        # continuing initialization.
        time.sleep(1)

        # Initializing the connection by passing a port to the Serial
        # constructor immediately opens the connection. It is not
        # necessary to call open() separately.
        object.__setattr__(
            self,
            "_connection",
            Serial(
                baudrate=self.serial_config.baudrate,
                bytesize=self.serial_config.bytesize,
                exclusive=self.serial_config.exclusive,
                parity=self.serial_config.parity,
                port=self._find_port().device,
                rtscts=self.serial_config.rtscts,
                stopbits=self.serial_config.stopbits,
                timeout=self.serial_config.timeout,
                write_timeout=self.serial_config.write_timeout,
            ),
        )

        self._opened_event.set()

        self._clean_buffer()

        # Start background threads.
        object.__setattr__(
            self,
            "_rx_dispatcher_thread",
            threading.Thread(target=self._rx_dispatcher),
        )
        self._rx_dispatcher_thread.start()

        object.__setattr__(
            self,
            "_tx_ordered_sender_thread",
            threading.Thread(target=self._tx_ordered_send),
        )
        self._tx_ordered_sender_thread.start()

        # Don't wait for a reply to this, just in case the device
        # doesn't support this command. The reply will still be
        # logged for debugging.
        self.send_message_no_reply(
            AptMessage_MGMSG_HW_REQ_INFO(
                destination=Address.GENERIC_USB,
                source=Address.HOST_CONTROLLER,
            )
        )

    def _close(self, e: BaseException | None = None) -> None:
        with self._open_close_lock:
            self._close_inner(e=e)

    # pylint: disable=R0912
    def _close_inner(self, e: BaseException | None) -> None:
        # For normal closes, when we haven't been given an exception,
        # we then want to ignore any other exceptions that the
        # connection worker threads might have experienced: odds are
        # good that those exceptions are a natural part of the
        # shutdown process.
        if e is not None:
            # However, for abnormal closes where we have been given an
            # exception, we should try to log exceptions that we've
            # captured from the worker threads.
            self.log.error(
                event=Event.APT_CONNECTION_ERROR,
                exc_info=e,
            )
            while True:
                try:
                    self.log.error(
                        event=Event.APT_CONNECTION_ERROR,
                        exc_info=self._close_exception_queue.get(block=False),
                    )
                except Empty:
                    break

        if self._closed_event.is_set():
            return

        try:
            self._shutdown_threads()
            self._tx_ordered_sender_thread.join()
            self._rx_dispatcher_thread.join()

            if self._connection.is_open:
                self._clean_buffer()
                self._connection.close()
        finally:
            self._closed_event.set()

        if e is not None:
            raise e

    def _shutdown_threads(self) -> None:
        self._opened_event.clear()
        self._tx_ordered_sender_queue.shutdown()
        with self._rx_dispatcher_subscribers_lock:
            for queue in self._rx_dispatcher_subscribers.values():
                queue.shutdown()

    # Receive dispatcher thread functions

    def _rx_dispatcher(self) -> None:
        try:
            with self._rx_lock:
                while self._fail_if_closed():
                    self._rx_dispatcher_internal_loop()
        except BaseException as e:  # pylint: disable=W0718
            self._close_exception_queue.put(e)
            self._shutdown_threads()

    def _rx_dispatcher_internal_loop(self) -> None:
        partial_message: None | AptMessageForStreamParsing = None
        full_message: Optional[AptMessage] = None
        message_bytes = self._serial_read_state_aware(6)
        partial_message = AptMessageForStreamParsing.from_bytes(message_bytes)
        message_id = partial_message.message_id
        if partial_message.data_length != 0:
            message_bytes = message_bytes + self._serial_read_state_aware(
                partial_message.data_length
            )

        if partial_message.message_id in AptMessageId:
            message_id = AptMessageId(partial_message.message_id)
            full_message = getattr(
                pnpq.apt.protocol, f"AptMessage_{message_id.name}"
            ).from_bytes(message_bytes)
            assert isinstance(full_message, AptMessage)
            self.log.debug(
                event=Event.RX_MESSAGE_KNOWN,
                message=full_message,
            )
            with self._rx_dispatcher_subscribers_lock:
                for queue in self._rx_dispatcher_subscribers.values():
                    queue.put(full_message)
        else:
            # Log and discard unknown messages: since we don't know
            # what they mean, it's likely that they are not necessary
            # for our API to function.
            self.log.error(
                event=Event.RX_MESSAGE_UNKNOWN,
                partial_message=partial_message,
                bytes=message_bytes,
            )

    def _serial_read_state_aware(self, size: int = 1) -> bytes:
        """We have set a serial read timeout. This timeout allows us
        to frequently check if the AptConnection object has been
        closed or is in the process of closing, and stop trying to
        read if that is the case.

        """
        output_bytes: bytes = bytes()
        while self._fail_if_closed():
            output_bytes = output_bytes + self._connection.read(size=size)
            if len(output_bytes) == size:
                return output_bytes
        return output_bytes

    # Transmit ordered send thread functions

    def _tx_ordered_send(self) -> None:
        try:
            while self._fail_if_closed():
                self._tx_ordered_send_internal_loop()
        except BaseException as e:  # pylint: disable=W0718
            self._close_exception_queue.put(e)
            self._shutdown_threads()

    def _tx_ordered_send_internal_loop(self) -> None:
        item = self._tx_ordered_sender_queue.get()
        if isinstance(item, _OrderedSenderQueueItemNoReply):
            self._tx_ordered_send_no_reply(item.message)
            self._tx_ordered_sender_queue.task_done()
            return
        assert isinstance(item, _OrderedSenderQueueItemExpectReply)
        self._tx_ordered_send_expect_reply(
            item.message, item.match_reply, item.reply_queue
        )
        self._tx_ordered_sender_queue.task_done()

    def _tx_ordered_send_no_reply(self, message: AptMessage) -> None:
        with self._tx_lock:
            self.log.debug(
                event=Event.TX_MESSAGE_ORDERED_NO_REPLY,
                message=message,
            )
            self._connection.write(message.to_bytes())
            # Some no-reply commands take time to complete. Sending
            # other messages while this is happening could cause the
            # device's internal software to fail until a hard reset is
            # peformed.
            #
            # This behavior has been observed with the
            # MGMSG_MOD_SET_CHANENABLESTATE message on the MPC320,
            # where rapidly toggling a channel off and then on again
            # seems to cause the device to stop responding to
            # commands.
            #
            # Unlike with reply-expected commands, below, this also
            # blocks any users of send_message_unordered.
            #
            # The sleep time set here is just a reasonable guess based
            # on observation of device behavior. It is not based on
            # information from the APT specification.
            time.sleep(0.2)

    def _tx_ordered_send_expect_reply(
        self,
        message: AptMessage,
        match_reply: Callable[
            [
                AptMessage,
            ],
            bool,
        ],
        reply_queue: Queue[AptMessage],
    ) -> None:
        # TODO We are subscribing to incoming messages just
        # *before* sending our message. Ideally we should
        # subscribe immediately *after* sending the
        # message. This is a little tricky to coordinate in
        # the current architecture.
        with (
            timeout(300) as check_timeout,
            self.subscribe() as receive_queue,
        ):
            with self._tx_lock:
                self.log.debug(
                    event=Event.TX_MESSAGE_ORDERED_EXPECT_REPLY,
                    message=message,
                )
                self._connection.write(message.to_bytes())
            # It doesn't seem to cause harm to let the sort of
            # messages we typically poll for using
            # send_message_unordered (REQ_USTATUSUPDATE,
            # ACK_USTATUSUPDATE) continue to be sent while we wait for
            # replies to messages, so we release the connection lock
            # here. Compare this to no-reply messages above, where we
            # block the sending of all messages for a short period of
            # time out of an abundance of caution.
            while check_timeout():
                message = receive_queue.get(timeout=300)
                if match_reply(message):
                    reply_queue.put(message)
                    receive_queue.task_done()
                    return
                receive_queue.task_done()
