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

SET_STATE_BAR_COMMAND = b"S 1\x0a"
SET_STATE_CROSS_COMMAND = b"S 2\x0a"
GET_STATUS_COMMAND = b"S?\x0a"
GET_QUERY_TYPE_COMMAND = b"T?\x0a"
GET_BOARD_NAME_COMMAND = b"I?\x0a"


class State(Enum):
    BAR = 1
    CROSS = 2


class AbstractOpticalSwitchThorlabs1310E(ABC):
    @abstractmethod
    def set_state(self, state: State) -> None:
        """Set the switch to the specified state."""

    @abstractmethod
    def get_status(self) -> State:
        """Get the current state of the switch."""

    # Get system information
    @abstractmethod
    def get_query_type(self) -> str:
        """Get the query type of the switch."""

    @abstractmethod
    def get_board_name(self) -> str:
        """Get the board name of the switch."""

    @abstractmethod
    def open(self) -> None:
        """Open the serial connection to the switch."""

    @abstractmethod
    def close(self) -> None:
        """Close the serial connection to the switch."""


@dataclass(frozen=True, kw_only=True)
class OpticalSwitchThorlabs1310E(AbstractOpticalSwitchThorlabs1310E):
    # Required
    serial_number: str

    # All other properties are optional.

    # Serial connection parameters. These defaults are used by all
    # known Thorlabs devices that implement the APT protocol and do
    # not need to be changed.
    baudrate: int = field(default=115200)
    bytesize: int = field(default=serial.EIGHTBITS)
    exclusive: bool = field(default=True)
    parity: str = field(default=serial.PARITY_NONE)
    rtscts: bool = field(default=True)
    stopbits: int = field(default=serial.STOPBITS_ONE)
    timeout: None | int = field(
        default=None  # None means wait forever, until the requested number of bytes are received
    )

    connection: Serial = field(init=False)

    # Add a mutex lock to ensure thread safety
    mutex_lock: Lock = field(default_factory=Lock)

    def __enter__(self) -> "OpticalSwitchThorlabs1310E":
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
            "connection",
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
        self.connection.flush()

        # Remove anything that might be left over in the buffer from
        # previous runs
        self.connection.reset_input_buffer()
        self.connection.reset_output_buffer()

    def close(self) -> None:
        with self.mutex_lock:
            if self.connection.is_open:
                self.connection.flush()
                self.connection.close()

    def set_state(self, state: State) -> None:
        with self.mutex_lock, timeout(3) as check_timeout:
            while check_timeout():
                if state == State.BAR:
                    self.connection.write(SET_STATE_BAR_COMMAND)
                elif state == State.CROSS:
                    self.connection.write(SET_STATE_CROSS_COMMAND)
                else:
                    raise ValueError(f"Unknown state: {state}")
                time.sleep(0.3)
                if self.__get_status() == state:
                    break

    def get_status(self) -> State:
        with self.mutex_lock:
            return self.__get_status()

    def __get_status(self) -> State:
        """Private method to get the status of the switch without locks. This is used to check the status during set_state."""
        self.connection.write(GET_STATUS_COMMAND)
        response = self.__read_serial_response()
        if response == b"1":
            return State.BAR
        if response == b"2":
            return State.CROSS
        raise ValueError(f"Unknown response: {response.decode('utf-8')}")

    def get_query_type(self) -> str:
        with self.mutex_lock:
            self.connection.write(GET_QUERY_TYPE_COMMAND)
            response = self.__read_serial_response()
            return response.decode("utf-8")

    def get_board_name(self) -> str:
        with self.mutex_lock:
            self.connection.write(GET_BOARD_NAME_COMMAND)
            response = self.__read_serial_response()
            return response.decode("utf-8")

    def __read_serial_response(self) -> bytes:
        """Read a response from the serial connection."""
        response = self.connection.read_until(b"\r\n")[:-2]  # Remove the trailing \r\n
        return response
