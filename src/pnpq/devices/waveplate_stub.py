import logging
import time

from pnpq.errors import (
    DevicePortNotFoundError,
    DeviceDisconnectedError,
    WavePlateMoveNotCompleted,
    WavePlateHomedNotCompleted,
    WavePlateGetPosNotCompleted,
    WavePlateCustomRotateError,
    WaveplateInvalidStepsError,
    WaveplateInvalidDegreeError,
    WaveplateEnableChannelError,
    WaveplateInvalidMotorChannelError,
)

class Waveplate:
    # conn: Serial
    # serial_number: str
    # port: str | None
    resolution: int
    max_steps: int
    relative_home: float

    def __init__(self):
        # Stub Serial Number
        # TODO: Custom serial number from initalizer
        self.device_sn = "stubwaveplate"

        self.resolution = 136533
        self.max_steps = 136533
        self.rotate_timeout = 10
        self.home_timeout = 20
        self.max_channel = 1
        self.auto_update = False
        # self.hub_connected = check_usb_hub_connected()

        self.logger = logging.getLogger(f"{self}")

        # Stub device parameters
        self.current_position = 0

        # Is connected to the device
        self.connected = False

        # Enabled channels (enable 1 by default)
        self.enabled_channels = [1]

    def __ensure_port_open(self) -> None:
        if not self.connected:
            self.logger.warning("Device not connected")
            raise DeviceDisconnectedError(f"{self} is disconnected")

    def __ensure_less_than_max_steps(self, steps: int) -> None:
        if steps > self.max_steps:
            raise WaveplateInvalidStepsError(f"Given steps: {steps} exceeds the maximum steps: {self.max_steps}")

    def __ensure_valid_degree(self, degree: float) -> None:
        if 0 <= degree <= 360:
            return
        raise WaveplateInvalidDegreeError(f"Invalid degree: {degree}. Degree must be in a range [0,360]")

    # Maybe make this into a function wrapper to remove some redundant code?
    def __stub_check_channel(self, chanid: int):
        return chanid in self.enabled_channels

    def connect(self):
        self.connected = True
        self.logger.info("Stub Waveplate Connected")

    def identify(self):
        self.__ensure_port_open()
        # Flashes LED on real device, for stub, we will do nothing
        self.logger.info("Stub Waveplate Identify")

    def home(self):
        self.__ensure_port_open()
        self.logger.info("Stub Waveplate Home")

        if not self.__stub_check_channel(1):
            # Do nothing if channel is not enabled
            return

        self.current_position = 0
        # Simulated delay for homing
        # TODO: Delay calculation
        time.sleep(1)
        self.logger.info(f"Home Position: {self.current_position}")

    def auto_update_start(self):
        self.__ensure_port_open()
        self.logger.info("Stub Waveplate Auto Update Start")
        # TODO: Auto updating logging

    def auto_update_stop(self):
        self.__ensure_port_open()
        self.logger.info("Stub Waveplate Auto Update Stop")
        # TODO: Auto updating logging

    def disable_channel(self, chanid: int):
        self.__ensure_port_open()
        self.logger.info(f"Stub Waveplate Disable Channel {chanid}")

        if chanid >= self.max_channel:
            raise WaveplateInvalidMotorChannelError(f"Channel {chanid} is not enabled")

        # Remove channel from enabled channels
        self.enabled_channels.remove(chanid)

        # Simulated delay
        time.sleep(0.1)

    def enable_channel(self, chanid: int):
        self.__ensure_port_open()
        self.logger.info(f"Stub Waveplate Enable Channel {chanid}")
        if chanid > self.max_channel:
            raise WaveplateInvalidMotorChannelError(f"Invalid motor channel: {chanid}. Max channel: {self.max_channel}")

        self.enabled_channels.append(chanid)

        # Simulated delay
        time.sleep(0.1)

        # TODO: Return a fake reply from the device

    def device_resolution(self) -> int:
        return self.resolution

    def getpos(self):
        self.__ensure_port_open()
        self.logger.info("Stub Waveplate Get Position")
        self.logger.info(f"Current Position: Steps: {self.current_position} Degrees: {self.current_position / self.resolution}")
        return self.current_position

    def rotate(self, degree: int | float):
        self.__ensure_port_open()
        self.__ensure_valid_degree(degree)

        if not self.__stub_check_channel(1):
            # Do nothing if channel is not enabled
            return

        self.logger.info(f"Stub Waveplate Rotate to {degree}")
        # Calculate number of steps to move
        movePosition = degree * self.resolution
        # Update current position
        self.current_position = movePosition
        # Delay to simulate rotation (for now: v=1ms/deg)
        time.sleep(abs(movePosition - self.current_position) / 1000)
        # TODO: Return a fake reply from the device

    def step_backward(self, steps: int):
        self.__ensure_port_open()
        self.__ensure_less_than_max_steps(steps)

        self.logger.info(f"Stub Waveplate Step Backware {steps}")

        if not self.__stub_check_channel(1):
            # Do nothing if channel is not enabled
            return

        # Make steps negative
        steps = -steps
        self.current_position += steps
        # Delay to simulate rotation (for now: v=1ms/deg)
        time.sleep(abs(steps) / 1000)

    def step_forward(self, steps: int):
        self.__ensure_port_open()
        self.__ensure_less_than_max_steps(steps)

        self.logger.info(f"Stub Waveplate Step Forward {steps}")

        if not self.__stub_check_channel(1):
            # Do nothing if channel is not enabled
            return

        self.current_position += steps
        # Delay to simulate rotation (for now: v=1ms/deg)
        time.sleep(abs(steps) / 1000)
        # In the future, maybe we can return a fake reply from the device

    def rotate_relative(self, degree: int | float):
        self.__ensure_port_open()
        self.__ensure_valid_degree(degree)

        self.logger.info(f"Stub Waveplate Rotate Relative {degree}")

        if not self.__stub_check_channel(1):
            # Do nothing if channel is not enabled
            return

        # Calculate number of steps to move
        movePosition = degree * self.resolution
        # Update current position
        self.current_position += movePosition
        # Delay to simulate rotation (for now: v=1ms/deg)
        time.sleep(abs(movePosition) / 1000)

    def custom_home(self, degree):
        self.__ensure_port_open()
        self.__ensure_valid_degree(degree)

        self.logger.info(f"Stub Waveplate Custom Home {degree}")

        if not self.__stub_check_channel(1):
            # Do nothing if channel is not enabled
            return

        self.home()
        self.relative_home = degree
        self.rotate(degree)

    def custom_rotate(self, degree):
        self.__ensure_port_open()
        self.__ensure_valid_degree(degree)

        self.logger.info(f"Stub Waveplate Custom Rotate {degree}")

        if not self.relative_home:
            # Do nothing if relative home is not set
            return

        if not self.relative_home:
            self.logger.error("Custom Home not set")
            raise WavePlateCustomRotateError("Waveplate({self}) relative_home not set")

        if not self.__stub_check_channel(1):
            # Do nothing if channel is not enabled
            return

        self.rotate(degree + self.relative_home)

    def __repr__(self) -> str:
        return f"Waveplate(Stub {self.device_sn})"
