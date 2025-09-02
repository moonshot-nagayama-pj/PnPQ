import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from types import TracebackType

import serial
import serial.tools.list_ports
from serial import Serial

from .utils import timeout


class State(Enum):
    BAR = 1
    CROSS = 2


class AbstractOpticalSwitchThorlabsE(ABC):
    """Provides a thread-safe and blocking API for interacting with the Thorlabs OSWxx-yyyyE series of optical switches.
    This driver has been tested on the `OSW22-1310E <https://www.thorlabs.com/thorproduct.cfm?partnumber=OSW22-1310E>`__.
    """

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
    def get_query_type(self) -> str:
        """Get the OSW board type code according to the configuration table."""

    @abstractmethod
    def get_board_name(self) -> str:
        """Get the name and the firmware version of the switch."""

    @abstractmethod
    def open(self) -> None:
        """Open the serial connection to the switch."""

    @abstractmethod
    def close(self) -> None:
        """Close the serial connection to the switch."""

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
    ``serial.Serial``. These defaults are used by all known Thorlabs
    devices that implement the APT protocol and should not need to be
    changed."""

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
    # Required

    serial_number: str

    # Optional

    # Serial connection parameters. The defaults are used by all known
    # devices supported by this class and do not need to be changed.
    serial_config: SerialConfig = field(default_factory=SerialConfig)

    # Private member variables
    _connection: Serial = field(init=False)

    # Add a mutex lock to ensure thread safety
    _communication_lock: Lock = field(default_factory=Lock, init=False)

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
                f"Serial number {self.serial_number} could not be found, failing intialization."
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

        time.sleep(0.1)
        self._connection.flush()

        # Remove anything that might be left over in the buffer from
        # previous runs
        self._connection.reset_input_buffer()
        self._connection.reset_output_buffer()

    def close(self) -> None:
        with self._communication_lock:
            if self._connection.is_open:
                self._connection.flush()
                self._connection.close()

    def set_state(self, state: State) -> None:
        with self._communication_lock, timeout(3) as check_timeout:
            # Generate command from the state's enum value
            command = f"S {state.value}\n".encode("utf-8")
            self._connection.write(command)

            while check_timeout():
                time.sleep(0.3)
                if self._get_state() == state:
                    break

    def get_state(self) -> State:
        with self._communication_lock:
            return self._get_state()

    def _get_state(self) -> State:
        """Private method to get the status of the switch without locks. This is used to check the status during set_state."""
        command = b"S?\n"
        self._connection.write(command)
        response = self._read_serial_response()
        return State(int(response.decode("utf-8")))

    def get_query_type(self) -> str:
        with self._communication_lock:
            command = b"T?\n"
            self._connection.write(command)
            response = self._read_serial_response()
            return response.decode("utf-8")

    def get_board_name(self) -> str:
        with self._communication_lock:
            command = b"I?\n"
            self._connection.write(command)
            response = self._read_serial_response()
            return response.decode("utf-8")

    def _read_serial_response(self) -> bytes:
        """Read a response from the serial connection."""
        response = self._connection.read_until(b"\r\n")[:-2]  # Remove the trailing \r\n
        return response
