import time, logging
import asyncio
from serial import Serial

from pnpq.errors import (
    DevicePortNotFoundError,
    DeviceDisconnectedError,
    WaveplateInvalidStepsError,
    WaveplateInvalidDegreeError,
)
from pnpq.utils import get_available_port

HW_SET_INFO_COMMAND = b"\x05\x00\x00\x00\x50\x01"
HOME_REQ_COMMAND = (
    b"\x40\x04\x0e\x00\xb2\x01\x00\x00\x00\x00\x00\x00\xa4\xaa\xbc\x08\x00\x00\x00\x00"
)
HOME_SET_COMMAND = b"\x41\x04\x01\x00\x50\x01"
HOME_MOVE_COMMAND = b"\x43\x04\x01\x00\x50\x01"
START_UPDATE_COMMAND = b"\x11\x00\x00\x00\x50\x01"
STOP_UPDATE_COMMAND = b"\x12\x00\x00\x00\x50\x01"
ROTATE_COMMAND = b"\x53\x04\x06\x00\xd0\x01\x00\x00"
ROTATE_REL_COMMAND = b"\x48\x04\x06\x00\xd0\x01\x00\x00"
SET_ENB_CHANNEL_COMMAND = b"\x10\x02\x00\x01\x50\x01"
REQ_ENB_CHANNEL_COMMAND = b"\x11\x02\x00\x01\x50\x01"


class Waveplate:
    conn: Serial
    serial_number: str
    port: str | None
    resolution: int
    max_steps: int
    relative_home: float

    def __init__(
        self,
        serial_port: str | None = None,
        serial_number: str | None = None,
    ):
        self.conn = Serial()
        self.conn.baudrate = 115200
        self.conn.bytesize = 8
        self.conn.stopbits = 1
        self.conn.parity = "N"
        self.conn.rtscts = True

        self.device_sn = serial_number
        if serial_port is not None:
            self.port = serial_port
            self.conn.port = self.port

        self.resolution = 136533
        self.max_steps = 136533
        self.rotate_timeout = 10
        self.home_timeout = 20
        self.max_channel = 1
        self.auto_update = False

        if self.device_sn is not None:
            self.conn.port = get_available_port(self.device_sn)
            if self.conn.port is None:
                raise DevicePortNotFoundError(
                    "Can not find Rotator WavePlate by serial_number (FTDI_SN)"
                )

        self.logger = logging.getLogger(f"{self}")

    def __ensure_port_open(self) -> None:
        if not self.conn.is_open:
            self.logger.warn("disconnected")
            raise DeviceDisconnectedError(f"{self} is disconnected")

    def __ensure_less_than_max_steps(self, steps: int) -> None:
        if steps > self.max_steps:
            raise WaveplateInvalidStepsError(
                f"the given steps: {steps} exceeds the device max steps: {self.max_steps}"
            )

    def __ensure_valid_degree(self, degree: float | int) -> None:
        if 0 <= degree <= 360:
            return
        raise WaveplateInvalidDegreeError(
            f"Invalid degree specified: {degree}. must be in a range [0,360]"
        )

    async def __async_wait_for_reply(
        self, sequence: bytes, num_retries: int
    ) -> bytes | None:
        start_time = time.time()
        # retries = num_retries
        while time.time() - start_time < num_retries:
            num_read_bytes = self.conn.in_waiting
            result = await self.conn.read(num_read_bytes)
            self.logger.debug(
                f"try to find sequence: {sequence}, result: {result}, retry count: {retries}"
            )

            if num_read_bytes > 0 and result.find(sequence) != -1:
                self.logger.debug(f"The sequence found")
                return result

        self.logger.warn(f"Can not received expected response from device")

    def __wait_for_reply(self, sequence: bytes, num_retries: int) -> bytes | None:
        retries = num_retries
        result: bytes = b""
        while retries > 0:
            num_read_bytes = self.conn.in_waiting

            result = self.conn.read(num_read_bytes)
            self.logger.debug(
                f"try to find sequence: {sequence}, results: {result}, retry count: {retries}"
            )

            # the sequence is found
            if num_read_bytes > 0 and result.find(sequence) != -1:
                self.logger.debug(f"The sequence found")
                return result

            time.sleep(1)
            retries -= 1

    def connect(self) -> None:
        self.logger.info("connecting...")
        self.conn.open()
        self.logger.info("connected")

    def identify(self) -> None:
        self.logger.info("call identify cmd")
        self.__ensure_port_open()
        self.conn.write(b"\x23\x02\x00\x00\x50\x01")
        # self.conn.write(b"\x23\x02\x00\x00\x32\x01")

    def async_home(self) -> bytes | None:
        self.logger.info("call home cmd")
        self.__ensure_port_open()

        self.conn.write(HOME_REQ_COMMAND)

        await asyncio.sleep(0.5)

        self.conn.write(HOME_SET_COMMAND)
        await asyncio.sleep(0.5)

        self.conn.write(HOME_MOVE_COMMAND)
        await asyncio.sleep(0.5)

        result = self.__wait_for_reply(b"\x44\x04", 20)
        self.logger.debug(f"home result: {result}")
        if result is None:
            self.logger.warn("home command is not completed")
        return result

    def home(self) -> bytes | None:
        self.logger.info("call home cmd")
        self.__ensure_port_open()

        self.conn.write(HOME_REQ_COMMAND)
        time.sleep(0.5)

        self.conn.write(HOME_SET_COMMAND)
        time.sleep(0.5)

        self.conn.write(HOME_MOVE_COMMAND)
        time.sleep(0.5)

        result = self.__wait_for_reply(b"\x44\x04", 20)
        self.logger.debug(f"home result: {result}")
        if result is None:
            self.logger.warn("home command is not completed")
        return result

    def auto_update_start(self) -> bytes | None:
        self.logger.info("cal auto update start cmd")
        self.__ensure_port_open()
        msg = START_UPDATE_COMMAND
        self.conn.write(msg)
        result = self.__wait_for_reply(b"\x81\x04", self.rotate_timeout)

        self.logger.debug(f"auto_update_start result: {result}")
        if result is None:
            self.logger.warn("auto update start command is not completed")
        else:
            self.auto_update = True
        return result

    def auto_update_stop(self) -> bytes | None:
        self.logger.info("cal auto update stop cmd")
        self.__ensure_port_open()
        msg = STOP_UPDATE_COMMAND
        self.conn.write(msg)
        result = self.__wait_for_reply(b"\x81\x04", 1)

        self.logger.debug(f"auto_update_stop result: {result}")
        if result is not None:
            self.logger.warn("auto update stop command is not completed")
        else:
            self.auto_update = False

        return result

    def disable_channel(self, chanid: int) -> bytes | None:
        self.logger.info("call disable_channel cmd")
        self.__ensure_port_open()

        if chanid >= self.max_channel:
            raise WavePlateInvalidMotorChannelError(
                f"Invalid channel ID specified: {chanid}. it must be 0 in K10CR1/M"
            )
        msg = b"\x10\x02\x00\x02\x50\x01"
        self.conn.write(msg)
        time.sleep(0.1)

    def enable_channel(self, chanid: int) -> bytes | None:
        self.logger.info("call enable_channel cmd")
        self.__ensure_port_open()

        if chanid >= self.max_channel:
            raise WavePlateInvalidMotorChannelError(
                f"Invalid channel ID specified: {chanid}. It must be in 0 for K10CR1/M"
            )

        # MGMSG_MOD_SET_CHANENABLESTATE 0x0210
        msg = SET_ENB_CHANNEL_COMMAND
        self.conn.write(msg)
        time.sleep(0.1)

        # MGMSG_MOD_REG_CHANENABLESTATE 0x0211
        msg = REQ_ENB_CHANNEL_COMMAND
        self.conn.write(msg)
        result = self.__wait_for_reply(b"\x12\x02", 4)

        # Waiting for GET_CHANENABLESTATE
        # MGMSG_MOD_REG_CHANENABLESTATE 0x0212
        self.logger.debug(f"enable channel result: {result}")
        if result is None:
            self.logger.warn("enable_channel command is not complete")
        return result

    def device_resolution(self) -> int:
        return self.resolution

    def getpos(self) -> float | None:
        self.logger.info("call getpos cmd")
        self.__ensure_port_open()

        # MGMSG_HW_START_UPDATEMSGS 0x0011
        msg = START_UPDATE_COMMAND
        self.conn.write(msg)

        result = self.__wait_for_reply(b"\x81\x04", self.rotate_timeout)
        self.logger.debug(f"getpos all byte sequence results: {result}")

        if not self.auto_update:
            # MSMSG_HW_STOP_UPDATEMSGS 0x0012
            msg = STOP_UPDATE_COMMAND
            self.conn.write(msg)

        if result is None:
            self.logger.warn("getpos command is not completed")
        else:
            pos_seq = result[8:12]
            self.logger.debug(f"getpos byte result: {pos_seq}")

            steps = int.from_bytes(pos_seq, byteorder="little")
            position = steps / self.resolution
            self.logger.info(f"getpos extracted result: pos:{position} steps:{steps}")
            return steps

    async def __async_rotator(self, degree: int | float) -> bytes | None:
        self.logger.info(f"call async rotate cmd: degree={degree}")
        # Absolute Rotation
        self.__ensure_port_open()
        self.__ensure_valid_degree(degree)

        msg = ROTATE_COMMAND + (int(degree * self.resolution)).to_bytes(
            4, byteorder="little"
        )
        self.conn.write(msg)

        result = self.__wait_for_reply(b"\x64\x04", self.rotate_timeout)

    def rotate(self, degree: int | float) -> bytes | None:
        self.logger.info(f"call rotate cmd: degree={degree}")
        # Absolute Rotation
        self.__ensure_port_open()
        self.__ensure_valid_degree(degree)

        msg = ROTATE_COMMAND + (int(degree * self.resolution)).to_bytes(
            4, byteorder="little"
        )
        self.conn.write(msg)

        result = self.__wait_for_reply(b"\x64\x04", self.rotate_timeout)
        if result is None:
            self.logger.warn("rotate command is not completed")
        return result

    def step_backward(self, steps: int) -> bytes | None:
        self.logger.info("call step_backward cmd")
        self.__ensure_port_open()
        # negate steps
        steps = -steps
        self.__ensure_less_than_max_steps(steps)

        # relative move
        msg = ROTATE_REL_COMMAND + (int(steps)).to_bytes(
            4, byteorder="little", signed=True
        )
        self.conn.write(msg)

        result = self.__wait_for_reply(b"\x64\x04", self.rotate_timeout)
        if result is None:
            self.logger.warn("step_backward command is not completed")
        return result

    def step_forward(self, steps: int) -> bytes | None:
        self.logger.info("call step_forward cmd")
        self.__ensure_port_open()
        self.__ensure_less_than_max_steps(steps)

        # relative
        msg = ROTATE_REL_COMMAND + (int(steps)).to_bytes(4, byteorder="little")
        self.conn.write(msg)

        result = self.__wait_for_reply(b"\x64\x04", self.rotate_timeout)
        if result is None:
            self.logger.warn("step_forward command is not completed")
        return result

    def rotate_relative(self, degree) -> bytes | None:
        self.logger.info(f"call rotate_relative cmd: degree={degree}")
        self.__ensure_port_open()
        self.__ensure_valid_degree(degree)

        msg = ROTATE_REL_COMMAND + (int(degree * self.resolution)).to_bytes(
            4, byteorder="little"
        )
        self.conn.write(msg)

        result = self.__wait_for_reply(b"\x64\x04", 10)
        if result is None:
            self.logger.warn("rotate command is not completed")
        return result

    def rotate_absolute(self, degree):
        self.logger.info(f"call rotate_absolute cmd: degree={degree}")
        self.__ensure_port_open()
        self.__ensure_valid_degree(degree)

        msg = ROTATE_COMMAND + (int(degree * self.resolution)).to_bytes(
            4, byteorder="little"
        )
        self.conn.write(msg)
        time.sleep(degree / 10)

    def custom_home(self, degree):
        self.logger.info(f"call custom_home cmd: degree={degree}")
        self.__ensure_port_open()
        self.__ensure_valid_degree(degree)

        self.home()
        self.relative_home = degree
        self.rotate(degree)

    def custom_rotate(self, degree):
        """Rotattion with customized home!"""

        if not self.relative_home:
            raise Exception("No relative homing is defined for rotation!")

        self.rotate(degree + self.relative_home)

    def __repr__(self) -> str:
        return f"Waveplate(Tholabs KB10CRM {self.conn.port})"
