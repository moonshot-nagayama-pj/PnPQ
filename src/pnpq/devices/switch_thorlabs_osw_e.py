import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from threading import Event, Lock
from types import TracebackType

import serial
import serial.tools.list_ports
from serial import Serial

from pnpq.errors import InvalidStateException

from .utils import timeout


class State(Enum):
    BAR = 1
    CROSS = 2


class AbstractOpticalSwitchThorlabsE(ABC):
    """Thread-safe, blocking API for the Thorlabs OSWxx-yyyyE series of optical switches."""

    @abstractmethod
    def set_state(self, state: State) -> None:
        """Set the switch to the specified state.
        This function is idempotent; if the switch is already in the desired state, setting it to the same state again will not cause an error.

        :param state: The state to set the switch to.
        """

    @abstractmethod
    def get_state(self) -> State:
        """Get the current state of the switch.

        :return: The current state of the switch.
        """

    # Get system information
    @abstractmethod
    def get_type_code(self) -> str:
        """:return: The board type code according to the configuration table, as a human-readable, unstructured string. The Thorlabs manual does not seem to explain what the configuration table is."""

    @abstractmethod
    def get_board_name(self) -> str:
        """:return: The switch name and firmware version as a human-readable, unstructured string."""

    @abstractmethod
    def open(self) -> None:
        """Open the serial connection to the switch.

        Once opened, attempting to call open() again will cause an :py:class:`InvalidStateException`.
        """

    @abstractmethod
    def close(self) -> None:
        """Close the serial connection to the switch.

        Once closed, attempting to re-open the connection will cause an :py:class:`InvalidStateException`.
        """

    @abstractmethod
    def __enter__(self) -> "AbstractOpticalSwitchThorlabsE":
        pass

    @abstractmethod
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        pass


@dataclass(frozen=True, kw_only=True)
class SerialConfig:
    """Serial connection configuration parameters, to be passed to
    ``serial.Serial``. The defaults are used by all known devices
    supported by this class and do not need to be changed.

    """

    baudrate: int = field(default=115200)
    bytesize: int = field(default=serial.EIGHTBITS)
    exclusive: bool = field(default=True)
    parity: str = field(default=serial.PARITY_NONE)
    rtscts: bool = field(default=True)
    stopbits: int = field(default=serial.STOPBITS_ONE)
    timeout: None | float = field(default=2.0)
    write_timeout: None | float = field(default=2.0)


@dataclass(frozen=True, kw_only=True)
class OpticalSwitchThorlabsE(AbstractOpticalSwitchThorlabsE):
    """
    Thread-safe, blocking driver for the Thorlabs OSWxx-yyyyE series of optical switches.

    This driver has been tested on the `OSW22-1310E <https://www.thorlabs.com/thorproduct.cfm?partnumber=OSW22-1310E>`__.

    Although this driver is cross-platform, it may have difficulty finding devices on MacOS and Linux. These problems can be resolved by modifying your system's udev configuration as described in :doc:`Getting Started with PnPQ </getting-started>`.

    :param serial_number: Required. The device's serial number, which may contain non-numeric characters. To add to the confusion, the serial number printed on the device's label may not be the same as the one visible via USB; on Linux, use ``lsusb -v`` to identify the correct value.
    :param serial_config: Optional. Serial connection parameters. The defaults are used by all known devices supported by this class and do not need to be changed.

    """

    # Required

    serial_number: str

    # Optional

    serial_config: SerialConfig = field(default_factory=SerialConfig)

    # Private

    _connection: Serial = field(init=False)
    _communication_lock: Lock = field(default_factory=Lock, init=False)
    _opened_event: Event = field(default_factory=Event, init=False)
    _closed_event: Event = field(default_factory=Event, init=False)

    def __enter__(self) -> "AbstractOpticalSwitchThorlabsE":
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def open(self) -> None:
        if self._opened_event.is_set():
            raise InvalidStateException(
                "Tried to re-open a connection that was already open."
            )
        if self._closed_event.is_set():
            raise InvalidStateException(
                "Tried to re-open a connection that was already closed."
            )
        with self._communication_lock:
            self._open()

    def _open(self) -> None:
        # These devices tend to take a few seconds to start up, and
        # this library tends to be used as part of services that start
        # automatically on computer boot. For safety, wait here before
        # continuing initialization.
        time.sleep(1)

        port_found = False
        port = None
        for possible_port in serial.tools.list_ports.comports():
            if possible_port.serial_number == self.serial_number:
                port = possible_port
                port_found = True
                break
        if not port_found:
            raise ValueError(
                f"Serial number {self.serial_number} could not be found, failing intialization. This may have been caused by a problem with your system's udev configuration. Check the PnPQ Getting Started guide for more information."
            )
        assert port is not None

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
                port=port.device,
                rtscts=self.serial_config.rtscts,
                stopbits=self.serial_config.stopbits,
                timeout=self.serial_config.timeout,
                write_timeout=self.serial_config.write_timeout,
            ),
        )
        self._clean_buffer()
        self._opened_event.set()

    def close(self) -> None:
        self._opened_event.clear()
        self._closed_event.set()
        with self._communication_lock:
            if self._connection.is_open:
                self._clean_buffer()
                self._connection.close()

    def set_state(self, state: State) -> None:
        self._fail_if_closed()
        with self._communication_lock, timeout(3) as check_timeout:
            # Generate command from the state's enum value
            command = f"S {state.value}\n".encode("utf-8")
            self._connection.write(command)

            while check_timeout():
                time.sleep(0.3)
                if self._get_state() == state:
                    break

    def get_state(self) -> State:
        self._fail_if_closed()
        with self._communication_lock:
            return self._get_state()

    def _get_state(self) -> State:
        """Private method to get the status of the switch without locks. This is used to check the status during set_state."""
        command = b"S?\n"
        self._connection.write(command)
        response = self._read_serial_response()
        return State(int(response.decode("utf-8")))

    def get_type_code(self) -> str:
        self._fail_if_closed()
        with self._communication_lock:
            command = b"T?\n"
            self._connection.write(command)
            response = self._read_serial_response()
            return response.decode("utf-8")

    def get_board_name(self) -> str:
        self._fail_if_closed()
        with self._communication_lock:
            command = b"I?\n"
            self._connection.write(command)
            response = self._read_serial_response()
            return response.decode("utf-8")

    def _read_serial_response(self) -> bytes:
        """Read a response from the serial connection."""
        response = self._connection.read_until(b"\r\n")[:-2]  # Remove the trailing \r\n
        return response

    def _clean_buffer(self) -> None:
        time.sleep(0.5)
        self._connection.flush()
        time.sleep(0.5)
        self._connection.reset_input_buffer()
        self._connection.reset_output_buffer()

    def _fail_if_closed(self) -> None:
        if (not self._opened_event.is_set()) or self._closed_event.is_set():
            raise InvalidStateException("Tried to use a closed switch object.")
