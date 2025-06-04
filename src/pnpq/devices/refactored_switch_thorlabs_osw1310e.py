#
# Thorlanbs Oprical Switch 1x2 and 2x2 1310E driver
#       OSW12-1310E & OSW22-1310E
#
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


import serial
import serial.tools.list_ports
from serial import Serial

class State(Enum):
    BAR = 1 # this might still trigger the pylint error
    CROSS = 2

class AbstractOpticalSwitchThorlabs1310E(ABC):
    @abstractmethod

    def connect(self) -> None:
        """Open a new connection."""
    
    @abstractmethod

    def set_state(self,state:State) -> None:
        """Set the switch to the specified state."""


@dataclass(frozen=True, kw_only=True)
class OpticalSwitchThorlabs1310E(AbstractOpticalSwitchThorlabs1310E):

    def __post_init__(
        self,
        serial_port: str | None = None,
        serial_number: str | None = None,
    ):
        self.conn = Serial()
        self.conn.baudrate = 115200
        self.conn.bytesize = 8
        self.conn.parity = "N"
        self.conn.rtscts = True

        self.port = serial_port
        self.conn.port = self.port
        self.device_sn = serial_number

        find_port = False
        if self.device_sn is not None:
            available_ports = serial.tools.list_ports.comports()
            for ports in available_ports:
                if ports.serial_number == self.device_sn:
                    self.conn.port = ports.device
                    find_port = True
                    break
            if not find_port:
                raise ValueError("Cannot find Switch by serial_number (FTDI_SN)")

    def connect(self) -> None:
        self.conn.open()


    def set_state(self,state:State) -> None:
        if state == State.BAR:
            self.conn.write(b"S 1\x0A")
        elif state == State.BAR:
            self.conn.write(b"S 2\x0A")
