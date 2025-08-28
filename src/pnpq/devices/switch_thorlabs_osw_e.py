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
class OpticalSwitchThorlabsE(AbstractOpticalSwitchThorlabsE):
    # Required
    serial_number: str

    # All other properties are optional.

    # Serial connection parameters.
    baudrate: int = field(default=115200)
    bytesize: int = field(default=serial.EIGHTBITS)
    exclusive: bool = field(default=True)
    parity: str = field(default=serial.PARITY_NONE)
    rtscts: bool = field(default=True)
    stopbits: int = field(default=serial.STOPBITS_ONE)
    timeout: None | int = field(
        default=None  # None means wait forever, until the requested number of bytes are received
    )

    __connection: Serial = field(init=False)

    # Add a mutex lock to ensure thread safety
    __communication_lock: Lock = field(default_factory=Lock, init=False)

    def __enter__(self) -> "OpticalSwitchThorlabsE":
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
        with self.__communication_lock:
            self.__open()

    def __open(self) -> None:
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
            "_OpticalSwitchThorlabs1310E__connection",
            Serial(
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                exclusive=self.exclusive,
                parity=self.parity,
                port=port.device,
                rtscts=self.rtscts,
                stopbits=self.stopbits,
                timeout=self.timeout,
            ),
        )

        time.sleep(0.1)
        self.__connection.flush()

        # Remove anything that might be left over in the buffer from
        # previous runs
        self.__connection.reset_input_buffer()
        self.__connection.reset_output_buffer()

    def close(self) -> None:
        with self.__communication_lock:
            if self.__connection.is_open:
                self.__connection.flush()
                self.__connection.close()

    def set_state(self, state: State) -> None:
        with self.__communication_lock, timeout(3) as check_timeout:
            # Generate command from the state's enum value
            command = f"S {state.value}\n".encode("utf-8")
            self.__connection.write(command)

            while check_timeout():
                time.sleep(0.3)
                if self.__get_state() == state:
                    break

    def get_state(self) -> State:
        with self.__communication_lock:
            return self.__get_state()

    def __get_state(self) -> State:
        """Private method to get the status of the switch without locks. This is used to check the status during set_state."""
        command = b"S?\n"
        self.__connection.write(command)
        response = self.__read_serial_response()
        return State(int(response.decode("utf-8")))

    def get_query_type(self) -> str:
        with self.__communication_lock:
            command = b"T?\n"
            self.__connection.write(command)
            response = self.__read_serial_response()
            return response.decode("utf-8")

    def get_board_name(self) -> str:
        with self.__communication_lock:
            command = b"I?\n"
            self.__connection.write(command)
            response = self.__read_serial_response()
            return response.decode("utf-8")

    def __read_serial_response(self) -> bytes:
        """Read a response from the serial connection."""
        response = self.__connection.read_until(b"\r\n")[
            :-2
        ]  # Remove the trailing \r\n
        return response
