#
# Thorlabs Optical Switch 1x2 and 2x2 1310E driver
#       OSW12-1310E & OSW22-1310E
#
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

import serial
import serial.tools.list_ports
from serial import Serial


class State(Enum):
    BAR = 1
    CROSS = 2


class AbstractOpticalSwitchThorlabs1310E(ABC):
    @abstractmethod
    def set_state(self, state: State) -> None:
        """Set the switch to the specified state."""


@dataclass(frozen=True, kw_only=True)
class OpticalSwitchThorlabs1310E(AbstractOpticalSwitchThorlabs1310E):
    # Required
    serial_number: str

    # Serial connection parameters
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
    def __post_init__(
        self,
    ) -> None:
        # These devices tend to take a few seconds to start up, and
        # this library tends to be used as part of services that start
        # automatically on computer boot. For safety, wait here before
        # continuing initialization.
        time.sleep(1)

        port_found = False
        port = None
        for port in serial.tools.list_ports.comports():
            if port.serial_number == self.serial_number:
                port_found = True
                break
        if not port_found:
            raise ValueError(
                f"Serial number {self.serial_number} could not be found, failing intialization."
            )
            
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
        
        # Remove anything that might be left over in the buffer from
        # previous runs
        self.connection.flush()
        time.sleep(1)
        self.connection.reset_input_buffer()
        self.connection.reset_output_buffer()

    def set_state(self, state: State) -> None:
        if state == State.BAR:
            self.conn.write(b"S 1\x0A")
        elif state == State.CROSS:
            self.conn.write(b"S 2\x0A")
