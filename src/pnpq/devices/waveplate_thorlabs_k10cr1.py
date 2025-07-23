import threading
import time
from abc import ABC, abstractmethod
from collections import UserDict
from dataclasses import dataclass, field
from typing import Any, cast

import structlog
from pint import Quantity

from ..apt.connection import AptConnection
from ..apt.protocol import (
    Address,
    AptMessage_MGMSG_HW_START_UPDATEMSGS,
    AptMessage_MGMSG_MOD_IDENTIFY,
    AptMessage_MGMSG_MOD_SET_CHANENABLESTATE,
    AptMessage_MGMSG_MOT_ACK_USTATUSUPDATE,
    AptMessage_MGMSG_MOT_GET_HOMEPARAMS,
    AptMessage_MGMSG_MOT_GET_JOGPARAMS,
    AptMessage_MGMSG_MOT_GET_STATUSUPDATE,
    AptMessage_MGMSG_MOT_GET_VELPARAMS,
    AptMessage_MGMSG_MOT_MOVE_ABSOLUTE,
    AptMessage_MGMSG_MOT_MOVE_COMPLETED_20_BYTES,
    AptMessage_MGMSG_MOT_MOVE_HOME,
    AptMessage_MGMSG_MOT_MOVE_HOMED,
    AptMessage_MGMSG_MOT_MOVE_JOG,
    AptMessage_MGMSG_MOT_REQ_HOMEPARAMS,
    AptMessage_MGMSG_MOT_REQ_JOGPARAMS,
    AptMessage_MGMSG_MOT_REQ_STATUSUPDATE,
    AptMessage_MGMSG_MOT_REQ_VELPARAMS,
    AptMessage_MGMSG_MOT_SET_HOMEPARAMS,
    AptMessage_MGMSG_MOT_SET_JOGPARAMS,
    AptMessage_MGMSG_MOT_SET_VELPARAMS,
    ChanIdent,
    EnableState,
    HomeDirection,
    JogDirection,
    JogMode,
    LimitSwitch,
    StopMode,
)
from ..units import pnpq_ureg


class WaveplateVelocityParams(UserDict[str, Quantity]):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.__setitem__("minimum_velocity", 20 * pnpq_ureg.k10cr1_velocity)
        self.__setitem__("acceleration", 0 * pnpq_ureg.k10cr1_acceleration)
        self.__setitem__("maximum_velocity", 120 * pnpq_ureg.k10cr1_velocity)

    def __setitem__(self, key: str, value: Quantity | None) -> None:
        if value is None:
            return

        if key in ("minimum_velocity", "maximum_velocity"):
            super().__setitem__(key, cast(Quantity, value.to("k10cr1_velocity")))
        elif key == "acceleration":
            super().__setitem__(key, cast(Quantity, value.to("k10cr1_acceleration")))
        else:
            raise ValueError(f"Invalid key '{key}'.")


class WaveplateJogParams(UserDict[str, Any]):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.__setitem__("jog_mode", JogMode.CONTINUOUS)
        self.__setitem__("jog_step_size", 1 * pnpq_ureg.k10cr1_step)
        self.__setitem__("jog_minimum_velocity", 0 * pnpq_ureg.k10cr1_velocity)
        self.__setitem__("jog_acceleration", 1 * pnpq_ureg.k10cr1_acceleration)
        self.__setitem__("jog_maximum_velocity", 10 * pnpq_ureg.k10cr1_velocity)
        self.__setitem__("jog_stop_mode", StopMode.IMMEDIATE)

    def __setitem__(self, key: str, value: Any) -> None:
        if value is None:
            return

        if key in ("jog_mode", "jog_stop_mode"):
            super().__setitem__(key, value)
        elif key == "jog_step_size":
            super().__setitem__(key, cast(Quantity, value.to("k10cr1_step")))
        elif key in ("jog_minimum_velocity", "jog_maximum_velocity"):
            super().__setitem__(key, cast(Quantity, value.to("k10cr1_velocity")))
        elif key == "jog_acceleration":
            super().__setitem__(key, cast(Quantity, value.to("k10cr1_acceleration")))
        else:
            raise ValueError(f"Invalid key '{key}'.")


class WaveplateHomeParams(UserDict[str, Any]):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.__setitem__("home_direction", HomeDirection.FORWARD)
        self.__setitem__("limit_switch", LimitSwitch.HARDWARE_FORWARD)
        self.__setitem__("home_velocity", 5 * pnpq_ureg.k10cr1_velocity)
        self.__setitem__("offset_distance", 0 * pnpq_ureg.k10cr1_step)

    def __setitem__(self, key: str, value: Any) -> None:
        if value is None:
            return

        if key == "home_direction":
            super().__setitem__(key, value)
        elif key == "limit_switch":
            super().__setitem__(key, value)
        elif key == "home_velocity":
            super().__setitem__(key, cast(Quantity, value.to("k10cr1_velocity")))
        elif key == "offset_distance":
            super().__setitem__(key, cast(Quantity, value.to("k10cr1_step")))
        else:
            raise ValueError(f"Invalid key '{key}'.")


class AbstractWaveplateThorlabsK10CR1(ABC):

    @abstractmethod
    def move_absolute(self, position: Quantity) -> None:
        """Move the waveplate to a certain angle.

        :param position: The angle to move to.
        """

    @abstractmethod
    def get_velparams(self) -> WaveplateVelocityParams:
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

    @abstractmethod
    def get_jogparams(self) -> WaveplateJogParams:
        """Request jog parameters from the device."""

    @abstractmethod
    def set_jogparams(
        self,
        jog_mode: None | JogMode = None,
        jog_step_size: None | Quantity = None,
        jog_minimum_velocity: None | Quantity = None,
        jog_acceleration: None | Quantity = None,
        jog_maximum_velocity: None | Quantity = None,
        jog_stop_mode: None | StopMode = None,
    ) -> None:
        """Set jog parameters on the device.

        :param jog_mode: The jog mode.
        :param jog_step_size: The jog step size.
        :param jog_minimum_velocity: The minimum velocity.
        :param jog_acceleration: The acceleration.
        :param jog_maximum_velocity: The maximum velocity.
        :param jog_stop_mode: The stop mode.
        """

    @abstractmethod
    def get_homeparams(self) -> WaveplateHomeParams:
        """Request home parameters from the device."""

    @abstractmethod
    def set_homeparams(
        self,
        home_direction: None | HomeDirection = None,
        limit_switch: None | LimitSwitch = None,
        home_velocity: None | Quantity = None,
        offset_distance: None | Quantity = None,
    ) -> None:
        """Set home parameters on the device.

        :param home_direction: The home direction.
        :param limit_switch: The limit switch.
        :param home_velocity: The home velocity.
        :param offset_distance: The offset distance.
        """

    @abstractmethod
    def jog(self, jog_direction: JogDirection) -> None:
        """Jog the waveplate in a certain direction.

        :param jog_direction: The direction to jog in.
        """

    @abstractmethod
    def home(self) -> None:
        """Move the waveplate to its home position."""

    @abstractmethod
    def identify(self) -> None:
        """Identify the device by blinking its LED."""

    @abstractmethod
    def is_homed(self) -> bool:
        """Check if the device is homed.
        Sends the REQ_STATUSUPDATE message and checks the HOMED status bit.

        Returns True if the device is homed, False otherwise.
        """


@dataclass(frozen=True, kw_only=True)
class WaveplateThorlabsK10CR1(AbstractWaveplateThorlabsK10CR1):
    _chan_ident = ChanIdent.CHANNEL_1

    connection: AptConnection
    home_on_init: bool = field(default=True)

    # Polling threads
    tx_poller_thread: threading.Thread = field(init=False)
    tx_poller_thread_lock: threading.Lock = field(default_factory=threading.Lock)

    log = structlog.get_logger()

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
            ),
        )

        homed = self.is_homed()

        if homed:
            self.log.info(
                "[Waveplate] Device is already homed, skipping homing on setup."
            )
        elif self.home_on_init:
            # Home the device on startup
            self.log.info("[Waveplate] Device is not homed, homing on setup.")

            # Set home velocity to 500 times the default amount
            # because the default amount is really slow
            self.set_homeparams(
                home_velocity=73291 * pnpq_ureg.k10cr1_velocity * 500,
            )
            time.sleep(1)
            self.home()

        else:
            self.log.info(
                "[Waveplate] Device is not homed, but skipping homing on setup because home_on_init is set to False.",
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

    def set_channel_enabled(self, enabled: bool) -> None:
        if enabled:
            chan_bitmask = self._chan_ident
        else:
            chan_bitmask = ChanIdent(0)

        self.connection.send_message_no_reply(  # K10CR1 doesn't reply after setting chan enable
            AptMessage_MGMSG_MOD_SET_CHANENABLESTATE(
                chan_ident=chan_bitmask,
                enable_state=EnableState.CHANNEL_ENABLED,
                destination=Address.GENERIC_USB,
                source=Address.HOST_CONTROLLER,
            ),
        )

    def identify(self) -> None:
        self.connection.send_message_no_reply(
            AptMessage_MGMSG_MOD_IDENTIFY(
                chan_ident=self._chan_ident,
                destination=Address.GENERIC_USB,
                source=Address.HOST_CONTROLLER,
            )
        )
        time.sleep(5)  # Allow time for the identify command to complete

    def move_absolute(self, position: Quantity) -> None:
        absolute_distance = round(position.to("k10cr1_step").magnitude)
        self.set_channel_enabled(True)
        self.log.debug("Sending move_absolute command...")
        start_time = time.perf_counter()
        self.connection.send_message_expect_reply(
            AptMessage_MGMSG_MOT_MOVE_ABSOLUTE(
                chan_ident=self._chan_ident,
                absolute_distance=absolute_distance,
                destination=Address.GENERIC_USB,
                source=Address.HOST_CONTROLLER,
            ),
            lambda message: (
                isinstance(message, AptMessage_MGMSG_MOT_MOVE_COMPLETED_20_BYTES)
                and message.chan_ident == self._chan_ident
                and message.position == absolute_distance
                and message.destination == Address.HOST_CONTROLLER
                and message.source == Address.GENERIC_USB
            ),
        )
        elapsed_time = time.perf_counter() - start_time
        self.log.debug("move_absolute command finished", elapsed_time=elapsed_time)

        self.set_channel_enabled(False)

    def get_velparams(self) -> WaveplateVelocityParams:

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

        result = WaveplateVelocityParams()
        result["minimum_velocity"] = params.minimum_velocity * pnpq_ureg.k10cr1_velocity
        result["acceleration"] = params.acceleration * pnpq_ureg.k10cr1_acceleration
        result["maximum_velocity"] = params.maximum_velocity * pnpq_ureg.k10cr1_velocity

        return result

    def set_velparams(
        self,
        minimum_velocity: None | Quantity = None,
        acceleration: None | Quantity = None,
        maximum_velocity: None | Quantity = None,
    ) -> None:

        # First get the current velocity parameters
        params = self.get_velparams()

        params["minimum_velocity"] = minimum_velocity
        params["acceleration"] = acceleration
        params["maximum_velocity"] = maximum_velocity

        self.connection.send_message_no_reply(
            AptMessage_MGMSG_MOT_SET_VELPARAMS(
                destination=Address.GENERIC_USB,
                source=Address.HOST_CONTROLLER,
                chan_ident=self._chan_ident,
                minimum_velocity=params["minimum_velocity"]
                .to(pnpq_ureg.k10cr1_velocity)
                .magnitude,
                acceleration=params["acceleration"]
                .to(pnpq_ureg.k10cr1_acceleration)
                .magnitude,
                maximum_velocity=params["maximum_velocity"]
                .to(pnpq_ureg.k10cr1_velocity)
                .magnitude,
            )
        )

    def get_jogparams(self) -> WaveplateJogParams:
        params = self.connection.send_message_expect_reply(
            AptMessage_MGMSG_MOT_REQ_JOGPARAMS(
                chan_ident=self._chan_ident,
                destination=Address.GENERIC_USB,
                source=Address.HOST_CONTROLLER,
            ),
            lambda message: (
                isinstance(message, AptMessage_MGMSG_MOT_GET_JOGPARAMS)
                and message.chan_ident == self._chan_ident
                and message.destination == Address.HOST_CONTROLLER
                and message.source == Address.GENERIC_USB
            ),
        )

        assert isinstance(params, AptMessage_MGMSG_MOT_GET_JOGPARAMS)

        result = WaveplateJogParams()
        result["jog_mode"] = params.jog_mode
        result["jog_step_size"] = params.jog_step_size * pnpq_ureg.k10cr1_step
        result["jog_minimum_velocity"] = (
            params.jog_minimum_velocity * pnpq_ureg.k10cr1_velocity
        )
        result["jog_minimum_velocity"] = (
            params.jog_minimum_velocity * pnpq_ureg.k10cr1_velocity
        )
        result["jog_acceleration"] = (
            params.jog_acceleration * pnpq_ureg.k10cr1_acceleration
        )
        result["jog_maximum_velocity"] = (
            params.jog_maximum_velocity * pnpq_ureg.k10cr1_velocity
        )
        result["jog_stop_mode"] = params.jog_stop_mode

        return result

    def set_jogparams(
        self,
        jog_mode: JogMode | None = None,
        jog_step_size: Quantity | None = None,
        jog_minimum_velocity: Quantity | None = None,
        jog_acceleration: Quantity | None = None,
        jog_maximum_velocity: Quantity | None = None,
        jog_stop_mode: StopMode | None = None,
    ) -> None:
        # First get the current jog parameters
        params = self.get_jogparams()

        params["jog_mode"] = jog_mode
        params["jog_step_size"] = jog_step_size
        params["jog_minimum_velocity"] = jog_minimum_velocity
        params["jog_acceleration"] = jog_acceleration
        params["jog_maximum_velocity"] = jog_maximum_velocity
        params["jog_stop_mode"] = jog_stop_mode

        self.connection.send_message_no_reply(
            AptMessage_MGMSG_MOT_SET_JOGPARAMS(
                destination=Address.GENERIC_USB,
                source=Address.HOST_CONTROLLER,
                chan_ident=self._chan_ident,
                jog_mode=params["jog_mode"],
                jog_step_size=params["jog_step_size"]
                .to(pnpq_ureg.k10cr1_step)
                .magnitude,
                jog_minimum_velocity=params["jog_minimum_velocity"]
                .to(pnpq_ureg.k10cr1_velocity)
                .magnitude,
                jog_acceleration=params["jog_acceleration"]
                .to(pnpq_ureg.k10cr1_acceleration)
                .magnitude,
                jog_maximum_velocity=params["jog_maximum_velocity"]
                .to(pnpq_ureg.k10cr1_velocity)
                .magnitude,
                jog_stop_mode=params["jog_stop_mode"],
            )
        )
        self.log.debug("set_jogparams", params=params)

    def get_homeparams(self) -> WaveplateHomeParams:
        params = self.connection.send_message_expect_reply(
            AptMessage_MGMSG_MOT_REQ_HOMEPARAMS(
                chan_ident=self._chan_ident,
                destination=Address.GENERIC_USB,
                source=Address.HOST_CONTROLLER,
            ),
            lambda message: (
                isinstance(message, AptMessage_MGMSG_MOT_GET_HOMEPARAMS)
                and message.chan_ident == self._chan_ident
                and message.destination == Address.HOST_CONTROLLER
                and message.source == Address.GENERIC_USB
            ),
        )

        assert isinstance(params, AptMessage_MGMSG_MOT_GET_HOMEPARAMS)

        result = WaveplateHomeParams()

        result["home_direction"] = params.home_direction
        result["limit_switch"] = params.limit_switch
        result["home_velocity"] = params.home_velocity * pnpq_ureg.k10cr1_velocity
        result["offset_distance"] = params.offset_distance * pnpq_ureg.k10cr1_step

        return result

    def set_homeparams(
        self,
        home_direction: HomeDirection | None = None,
        limit_switch: LimitSwitch | None = None,
        home_velocity: Quantity | None = None,
        offset_distance: Quantity | None = None,
    ) -> None:
        # First get the current home parameters
        params = self.get_homeparams()

        params["home_direction"] = home_direction
        params["limit_switch"] = limit_switch
        params["home_velocity"] = home_velocity
        params["offset_distance"] = offset_distance

        self.connection.send_message_no_reply(
            AptMessage_MGMSG_MOT_SET_HOMEPARAMS(
                destination=Address.GENERIC_USB,
                source=Address.HOST_CONTROLLER,
                chan_ident=self._chan_ident,
                home_direction=params["home_direction"],
                limit_switch=params["limit_switch"],
                home_velocity=params["home_velocity"]
                .to(pnpq_ureg.k10cr1_velocity)
                .magnitude,
                offset_distance=params["offset_distance"]
                .to(pnpq_ureg.k10cr1_step)
                .magnitude,
            )
        )

    def home(self) -> None:
        self.set_channel_enabled(True)
        start_time = time.perf_counter()
        self.connection.send_message_expect_reply(
            AptMessage_MGMSG_MOT_MOVE_HOME(
                chan_ident=self._chan_ident,
                destination=Address.GENERIC_USB,
                source=Address.HOST_CONTROLLER,
            ),
            lambda message: (
                isinstance(message, AptMessage_MGMSG_MOT_MOVE_HOMED)
                and message.chan_ident == self._chan_ident
                and message.destination == Address.HOST_CONTROLLER
                and message.source == Address.GENERIC_USB
            ),
        )
        elapsed_time = time.perf_counter() - start_time
        self.log.debug("home command finished", elapsed_time=elapsed_time)
        self.set_channel_enabled(False)

    def jog(self, jog_direction: JogDirection) -> None:
        self.set_channel_enabled(True)
        self.connection.send_message_expect_reply(
            AptMessage_MGMSG_MOT_MOVE_JOG(
                chan_ident=self._chan_ident,
                jog_direction=jog_direction,
                destination=Address.GENERIC_USB,
                source=Address.HOST_CONTROLLER,
            ),
            lambda message: (
                isinstance(message, AptMessage_MGMSG_MOT_MOVE_COMPLETED_20_BYTES)
                and message.chan_ident == self._chan_ident
                and message.destination == Address.HOST_CONTROLLER
                and message.source == Address.GENERIC_USB
            ),
        )
        self.set_channel_enabled(False)

    def is_homed(self) -> bool:

        # Maybe possible to wait for status update instead?
        # Because autoupdate messages are sent every second
        # Also, according to the protocol, K10CR1 should not
        # support REQ_STATUSUPDATE, but upon testing, it does.
        status_message = self.connection.send_message_expect_reply(
            AptMessage_MGMSG_MOT_REQ_STATUSUPDATE(
                chan_ident=self._chan_ident,
                destination=Address.GENERIC_USB,
                source=Address.HOST_CONTROLLER,
            ),
            lambda message: (
                isinstance(message, AptMessage_MGMSG_MOT_GET_STATUSUPDATE)
                and message.destination == Address.HOST_CONTROLLER
                and message.source == Address.GENERIC_USB
            ),
        )
        assert isinstance(status_message, AptMessage_MGMSG_MOT_GET_STATUSUPDATE)
        return status_message.status.HOMED
