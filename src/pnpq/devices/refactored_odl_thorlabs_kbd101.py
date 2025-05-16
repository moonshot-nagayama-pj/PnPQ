import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TypedDict, cast

import structlog
from pint import Quantity

from ..apt.connection import AptConnection
from ..apt.protocol import (
    Address,
    AptMessage_MGMSG_HW_START_UPDATEMSGS,
    AptMessage_MGMSG_MOD_IDENTIFY,
    AptMessage_MGMSG_MOD_SET_CHANENABLESTATE,
    AptMessage_MGMSG_MOT_ACK_USTATUSUPDATE,
    AptMessage_MGMSG_MOT_GET_VELPARAMS,
    AptMessage_MGMSG_MOT_MOVE_ABSOLUTE,
    AptMessage_MGMSG_MOT_MOVE_COMPLETED_20_BYTES,
    AptMessage_MGMSG_MOT_MOVE_HOME,
    AptMessage_MGMSG_MOT_MOVE_STOPPED_20_BYTES,
    AptMessage_MGMSG_MOT_REQ_VELPARAMS,
    AptMessage_MGMSG_MOT_SET_VELPARAMS,
    ChanIdent,
    EnableState,
)
from ..units import pnpq_ureg


# TODO: This is set as a separate class for now.
# If the Thorlabs waveplates use exactly the same logic, we might be able to combine them
class OpticalDelayLineVelocityParams(TypedDict):
    """TypedDict for waveplate velocity parameters.
    Used in `get_velparams` method.
    """

    #: Dimensionality must be ([angle] / [time]) or kbd101_velocity
    minimum_velocity: Quantity
    #: Dimensionality must be ([angle] / [time] ** 2) or kbd101_acceleration
    acceleration: Quantity
    #: Dimensionality must be ([angle] / [time]) or kbd101_velocity
    maximum_velocity: Quantity


class AbstractOpticalDelayLineThorlabsKBD101(ABC):

    @abstractmethod
    def identify(self) -> None:
        """Identifies the device represented by this instance
        by flashing the light on the device.

        :param chan_ident: The motor channel to identify.

        """

    @abstractmethod
    def home(self) -> None:
        """Move the device to home position."""

    @abstractmethod
    def move_absolute(self, position: Quantity) -> None:
        """Move the waveplate to a certain angle.

        :param position: The angle to move to.
        """

    @abstractmethod
    def get_velparams(self) -> OpticalDelayLineVelocityParams:
        """Request velocity parameters from the device."""

    @abstractmethod
    def set_velparams(
        self,
        minimum_velocity: None | Quantity = None,
        acceleration: None | Quantity = None,
        maximum_velocity: None | Quantity = None,
    ) -> None:
        """Set velocity parameters on the device.

        :param minimum_velocity: The minimum velocity. According to the
            documentation, this should always be 0. Therefore this parameter
            can be left unused.
        :param acceleration: The acceleration.
        :param maximum_velocity: The maximum velocity.
        """


@dataclass(frozen=True, kw_only=True)
class OpticalDelayLineThorlabsKBD101(AbstractOpticalDelayLineThorlabsKBD101):
    _chan_ident = ChanIdent.CHANNEL_1

    connection: AptConnection

    # Polling threads
    tx_poller_thread: threading.Thread = field(init=False)
    tx_poller_thread_lock: threading.Lock = field(default_factory=threading.Lock)

    log = structlog.get_logger()

    # Setup channels for the device
    available_channels: frozenset[ChanIdent] = frozenset([ChanIdent.CHANNEL_1])

    def __post_init__(self) -> None:
        # Start polling thread
        object.__setattr__(
            self,
            "tx_poller_thread",
            threading.Thread(target=self.tx_poll, daemon=True),
        )

        self.tx_poller_thread.start()

        # Send autoupdate
        self.connection.send_message_no_reply(
            AptMessage_MGMSG_HW_START_UPDATEMSGS(
                destination=Address.GENERIC_USB,
                source=Address.HOST_CONTROLLER,
            )
        )

    # Polling thread for sending status update requests
    def tx_poll(self) -> None:
        with self.tx_poller_thread_lock:
            while True:
                self.connection.send_message_unordered(
                    AptMessage_MGMSG_MOT_ACK_USTATUSUPDATE(
                        destination=Address.GENERIC_USB,
                        source=Address.HOST_CONTROLLER,
                    )
                )
                # If we are currently waiting for a reply to a message
                # we sent, poll every 0.2 seconds to ensure a
                # relatively quick response to state changes that we
                # observe using status update messages. If we are not
                # waiting for a reply, poll at least once every second
                # to reduce the amount of noise in logs.
                #
                # The tx_ordered_sender thread can request a faster
                # update by setting the
                # tx_ordered_sender_awaiting_reply event.
                if self.connection.tx_ordered_sender_awaiting_reply.is_set():
                    time.sleep(0.2)
                else:
                    # The documentation for
                    # MGMSG_MOT_ACK_USTATUSUPDATE suggests that it
                    # should be sent at least once a second. This will
                    # probably send slightly less frequently than once
                    # a second, so, if we start having issues, we
                    # should decrease this interval.
                    self.connection.tx_ordered_sender_awaiting_reply.wait(0.9)

    def identify(self) -> None:
        self.connection.send_message_no_reply(
            AptMessage_MGMSG_MOD_IDENTIFY(
                chan_ident=ChanIdent.CHANNEL_1,
                destination=Address.GENERIC_USB,
                source=Address.HOST_CONTROLLER,
            )
        )

    def set_channel_enabled(self, enabled: bool) -> None:
        if enabled:
            chan_bitmask = self._chan_ident
        else:
            chan_bitmask = ChanIdent(0)

        self.connection.send_message_no_reply(
            AptMessage_MGMSG_MOD_SET_CHANENABLESTATE(
                chan_ident=chan_bitmask,
                enable_state=EnableState.CHANNEL_ENABLED,
                destination=Address.GENERIC_USB,
                source=Address.HOST_CONTROLLER,
            ),
        )

    def home(self) -> None:
        self.set_channel_enabled(True)
        start_time = time.perf_counter()
        result = self.connection.send_message_expect_reply(
            AptMessage_MGMSG_MOT_MOVE_HOME(
                chan_ident=self._chan_ident,
                destination=Address.GENERIC_USB,
                source=Address.HOST_CONTROLLER,
            ),
            lambda message: (
                isinstance(
                    message,
                    (
                        AptMessage_MGMSG_MOT_MOVE_COMPLETED_20_BYTES,
                        AptMessage_MGMSG_MOT_MOVE_STOPPED_20_BYTES,
                    ),
                )
                and message.chan_ident == self._chan_ident
                and message.destination == Address.HOST_CONTROLLER
                and message.source == Address.GENERIC_USB
            ),
        )
        # Sometimes the move stopped is received when interrupted
        # by the user or when an invalid position is given
        if isinstance(result, AptMessage_MGMSG_MOT_MOVE_STOPPED_20_BYTES):
            self.log.error(
                "move_absolute command failed",
                error="Move stopped before completion",
            )
            raise RuntimeError("Move stopped before completion")

        elapsed_time = time.perf_counter() - start_time
        self.log.debug("home command finished", elapsed_time=elapsed_time)
        self.set_channel_enabled(False)

    def move_absolute(self, position: Quantity) -> None:
        absolute_distance = round(position.to("kbd101_position").magnitude)
        self.set_channel_enabled(True)
        self.log.debug("Sending move_absolute command...")
        start_time = time.perf_counter()

        result = self.connection.send_message_expect_reply(
            AptMessage_MGMSG_MOT_MOVE_ABSOLUTE(
                chan_ident=self._chan_ident,
                absolute_distance=absolute_distance,
                destination=Address.GENERIC_USB,
                source=Address.HOST_CONTROLLER,
            ),
            lambda message: (
                isinstance(
                    message,
                    (
                        AptMessage_MGMSG_MOT_MOVE_COMPLETED_20_BYTES,
                        AptMessage_MGMSG_MOT_MOVE_STOPPED_20_BYTES,
                    ),
                )
                and message.chan_ident == self._chan_ident
                and message.destination == Address.HOST_CONTROLLER
                and message.source == Address.GENERIC_USB
            ),
        )
        # Sometimes the move stopped is received when interrupted
        # by the user or when an invalid position is given
        if isinstance(result, AptMessage_MGMSG_MOT_MOVE_STOPPED_20_BYTES):
            self.log.error(
                "move_absolute command failed",
                error="Move stopped before completion",
            )
            raise RuntimeError("Move stopped before completion")

        # If move is completed, check if the position is within 1mm of the target
        assert isinstance(result, AptMessage_MGMSG_MOT_MOVE_COMPLETED_20_BYTES)
        if (
            result.position > absolute_distance - 1000
            and result.position < absolute_distance + 1000
        ):
            self.log.error("Invalid position was matched")
            raise RuntimeError("Invalid position was matched")

        elapsed_time = time.perf_counter() - start_time
        self.log.debug("move_absolute command finished", elapsed_time=elapsed_time)

        self.set_channel_enabled(False)

    def get_velparams(self) -> OpticalDelayLineVelocityParams:

        params = self.connection.send_message_expect_reply(
            AptMessage_MGMSG_MOT_REQ_VELPARAMS(
                chan_ident=self._chan_ident,
                destination=Address.GENERIC_USB,
                source=Address.HOST_CONTROLLER,
            ),
            lambda message: (
                isinstance(message, AptMessage_MGMSG_MOT_GET_VELPARAMS)
                and message.chan_ident == self._chan_ident
                and message.destination == Address.HOST_CONTROLLER
                and message.source == Address.GENERIC_USB
            ),
        )
        assert isinstance(params, AptMessage_MGMSG_MOT_GET_VELPARAMS)

        result: OpticalDelayLineVelocityParams = {
            "minimum_velocity": params.minimum_velocity * pnpq_ureg.kbd101_velocity,
            "acceleration": params.acceleration * pnpq_ureg.kbd101_acceleration,
            "maximum_velocity": params.maximum_velocity * pnpq_ureg.kbd101_velocity,
        }
        return result

    def set_velparams(
        self,
        minimum_velocity: None | Quantity = None,
        acceleration: None | Quantity = None,
        maximum_velocity: None | Quantity = None,
    ) -> None:

        # First get the current velocity parameters
        params = self.get_velparams()

        if minimum_velocity is not None:
            params["minimum_velocity"] = cast(
                Quantity, minimum_velocity.to("kbd101_velocity")
            )
        if acceleration is not None:
            params["acceleration"] = cast(
                Quantity, acceleration.to("kbd101_acceleration")
            )
        if maximum_velocity is not None:
            params["maximum_velocity"] = cast(
                Quantity, maximum_velocity.to("kbd101_velocity")
            )

        self.connection.send_message_no_reply(
            AptMessage_MGMSG_MOT_SET_VELPARAMS(
                destination=Address.GENERIC_USB,
                source=Address.HOST_CONTROLLER,
                chan_ident=self._chan_ident,
                minimum_velocity=params["minimum_velocity"]
                .to(pnpq_ureg.kbd101_velocity)
                .magnitude,
                acceleration=params["acceleration"]
                .to(pnpq_ureg.kbd101_acceleration)
                .magnitude,
                maximum_velocity=params["maximum_velocity"]
                .to(pnpq_ureg.kbd101_velocity)
                .magnitude,
            )
        )
