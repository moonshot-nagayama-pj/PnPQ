import threading
import time
from abc import ABC, abstractmethod
from collections import UserDict
from dataclasses import dataclass, field
from typing import Any, cast

import structlog
from pint import Quantity

from ..apt.connection import AbstractAptConnection
from ..apt.protocol import (
    Address,
    AptMessage_MGMSG_HW_START_UPDATEMSGS,
    AptMessage_MGMSG_MOD_IDENTIFY,
    AptMessage_MGMSG_MOD_SET_CHANENABLESTATE,
    AptMessage_MGMSG_MOT_ACK_USTATUSUPDATE,
    AptMessage_MGMSG_MOT_GET_HOMEPARAMS,
    AptMessage_MGMSG_MOT_GET_JOGPARAMS,
    AptMessage_MGMSG_MOT_GET_USTATUSUPDATE,
    AptMessage_MGMSG_MOT_GET_VELPARAMS,
    AptMessage_MGMSG_MOT_MOVE_ABSOLUTE,
    AptMessage_MGMSG_MOT_MOVE_COMPLETED_20_BYTES,
    AptMessage_MGMSG_MOT_MOVE_HOME,
    AptMessage_MGMSG_MOT_MOVE_HOMED,
    AptMessage_MGMSG_MOT_MOVE_JOG,
    AptMessage_MGMSG_MOT_MOVE_STOPPED_20_BYTES,
    AptMessage_MGMSG_MOT_REQ_HOMEPARAMS,
    AptMessage_MGMSG_MOT_REQ_JOGPARAMS,
    AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE,
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
from ..events import Event
from ..units import pnpq_ureg


class OpticalDelayLineVelocityParams(UserDict[str, Any]):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.__setitem__("minimum_velocity", 0 * pnpq_ureg.kbd101_velocity)
        self.__setitem__("acceleration", 0 * pnpq_ureg.kbd101_acceleration)
        self.__setitem__("maximum_velocity", 10 * pnpq_ureg.kbd101_velocity)

    def __setitem__(self, key: str, value: Any) -> None:
        if value is None:
            return

        if key in ("minimum_velocity", "maximum_velocity"):
            super().__setitem__(key, cast(Quantity, value.to("kbd101_velocity")))
        elif key == "acceleration":
            super().__setitem__(key, cast(Quantity, value.to("kbd101_acceleration")))
        else:
            raise ValueError(f"Invalid key '{key}'.")


class OpticalDelayLineJogParams(UserDict[str, Any]):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.__setitem__("jog_mode", JogMode.SINGLE_STEP)
        self.__setitem__("jog_step_size", 20000 * pnpq_ureg.kbd101_position)
        self.__setitem__("jog_minimum_velocity", 134218 * pnpq_ureg.kbd101_velocity)
        self.__setitem__("jog_acceleration", 7 * pnpq_ureg.kbd101_acceleration)
        self.__setitem__("jog_maximum_velocity", 134218 * pnpq_ureg.kbd101_velocity)
        self.__setitem__("jog_stop_mode", StopMode.CONTROLLED)

    def __setitem__(self, key: str, value: Any) -> None:

        # TODO When setting an invalid key to None, ValueError is not raised. Fix this for all Params UserDicts.
        if value is None:
            return

        if key in ("jog_mode", "jog_stop_mode"):
            super().__setitem__(key, value)
        elif key == "jog_step_size":
            super().__setitem__(key, cast(Quantity, value.to("kbd101_position")))
        elif key in ("jog_minimum_velocity", "jog_maximum_velocity"):
            super().__setitem__(key, cast(Quantity, value.to("kbd101_velocity")))
        elif key == "jog_acceleration":
            super().__setitem__(key, cast(Quantity, value.to("kbd101_acceleration")))
        else:
            raise ValueError(f"Invalid key '{key}'.")


class OpticalDelayLineHomeParams(UserDict[str, Any]):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.__setitem__("home_direction", HomeDirection.FORWARD)
        self.__setitem__("limit_switch", LimitSwitch.HARDWARE_FORWARD)
        self.__setitem__("home_velocity", 134218 * pnpq_ureg.kbd101_velocity)
        self.__setitem__("offset_distance", 0 * pnpq_ureg.kbd101_position)

    def __setitem__(self, key: str, value: Any) -> None:
        if value is None:
            return

        if key in ("home_direction", "limit_switch"):
            super().__setitem__(key, value)
        elif key == "home_velocity":
            super().__setitem__(key, cast(Quantity, value.to("kbd101_velocity")))
        elif key == "offset_distance":
            super().__setitem__(key, cast(Quantity, value.to("kbd101_position")))
        else:
            raise ValueError(f"Invalid key '{key}'.")


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
        """Move the device to the specified position.

        :param position: The angle to move to.
        """

    @abstractmethod
    def jog(self, jog_direction: JogDirection) -> None:
        """Jog the device in a certain direction.

        :param jog_direction: The direction to jog in.
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

        All parameters of this function are optional. Only fields
        with values are updated on the device.

        :param minimum_velocity: The minimum velocity. According to the
            documentation, this should always be 0. Therefore this parameter
            can be left unused.
        :param acceleration: The acceleration.
        :param maximum_velocity: The maximum velocity.
        """

    @abstractmethod
    def get_homeparams(self) -> OpticalDelayLineHomeParams:
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

        All parameters of this function are optional. Only fields
        with values are updated on the device.

        :param home_direction: The home direction.
        :param limit_switch: The limit switch.
        :param home_velocity: The home velocity.
        :param offset_distance: The offset distance.
        """

    @abstractmethod
    def get_jogparams(self) -> OpticalDelayLineJogParams:
        """Request jog parameters from the device."""

    @abstractmethod
    def set_jogparams(
        self,
        jog_mode: JogMode | None = None,
        jog_step_size: Quantity | None = None,
        jog_minimum_velocity: Quantity | None = None,
        jog_acceleration: Quantity | None = None,
        jog_maximum_velocity: Quantity | None = None,
        jog_stop_mode: StopMode | None = None,
    ) -> None:
        """Set jog parameters on the device.

        All parameters of this function are optional. Only fields
        with values are updated on the device.

        :param jog_mode: The jog mode.
        :param jog_step_size: The jog step size.
        :param jog_minimum_velocity: The minimum velocity.
        :param jog_acceleration: The acceleration.
        :param jog_maximum_velocity: The maximum velocity.
        :param jog_stop_mode: The stop mode.
        """

    @abstractmethod
    def get_status(self) -> AptMessage_MGMSG_MOT_GET_USTATUSUPDATE:
        """Request the latest status message from the device."""


@dataclass(frozen=True, kw_only=True)
class OpticalDelayLineThorlabsKBD101(AbstractOpticalDelayLineThorlabsKBD101):
    _chan_ident = ChanIdent.CHANNEL_1

    connection: AbstractAptConnection = field()
    home_on_init: bool = field(default=True)

    # Polling threads
    _poller_thread: threading.Thread = field(init=False)
    _stop_poller_event: threading.Event = field(
        default_factory=threading.Event, init=False
    )

    log = structlog.get_logger()

    def __post_init__(self) -> None:
        # Start polling thread
        object.__setattr__(
            self,
            "_poller_thread",
            threading.Thread(target=self._poller),
        )
        self._poller_thread.start()

        # Send autoupdate
        self.connection.send_message_no_reply(
            AptMessage_MGMSG_HW_START_UPDATEMSGS(
                destination=Address.GENERIC_USB,
                source=Address.HOST_CONTROLLER,
            )
        )

        current_status = self.get_status()
        is_homed = current_status.status.HOMED
        if is_homed:
            self.log.info("[ODL] Device is already homed, skipping homing on setup.")
        elif self.home_on_init:
            self.log.info("[ODL] Device is not homed, homing on setup.")
            time.sleep(0.1)
            self.home()
        else:
            self.log.info(
                "[ODL] Device is not homed, but skipping homing on setup because home_on_init is set to False.",
            )

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
                        AptMessage_MGMSG_MOT_MOVE_HOMED,
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

    def get_status(self) -> AptMessage_MGMSG_MOT_GET_USTATUSUPDATE:
        msg = self.connection.send_message_expect_reply(
            AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE(
                chan_ident=self._chan_ident,
                destination=Address.GENERIC_USB,
                source=Address.HOST_CONTROLLER,
            ),
            lambda message: (
                isinstance(message, AptMessage_MGMSG_MOT_GET_USTATUSUPDATE)
                and message.chan_ident == self._chan_ident
                and message.destination == Address.HOST_CONTROLLER
                and message.source == Address.GENERIC_USB
            ),
        )
        return cast(AptMessage_MGMSG_MOT_GET_USTATUSUPDATE, msg)

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
        if not (
            result.position > absolute_distance - 1000
            and result.position < absolute_distance + 1000
        ):
            self.log.error(
                "Invalid position was matched: %s (expected %s)",
                result.position,
                absolute_distance,
            )
            raise RuntimeError("Invalid position was matched")

        elapsed_time = time.perf_counter() - start_time
        self.log.debug("move_absolute command finished", elapsed_time=elapsed_time)

        self.set_channel_enabled(False)

    def jog(self, jog_direction: JogDirection) -> None:
        # TODO: Validate this function when the device is in continuous jog mode
        #
        # TODO: Fuzzy-match the stop position in the same way move_absolute does
        result = self.connection.send_message_expect_reply(
            AptMessage_MGMSG_MOT_MOVE_JOG(
                chan_ident=self._chan_ident,
                jog_direction=jog_direction,
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

        result = OpticalDelayLineVelocityParams()
        result["minimum_velocity"] = params.minimum_velocity * pnpq_ureg.kbd101_velocity
        result["acceleration"] = params.acceleration * pnpq_ureg.kbd101_acceleration
        result["maximum_velocity"] = params.maximum_velocity * pnpq_ureg.kbd101_velocity

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

    def get_homeparams(self) -> OpticalDelayLineHomeParams:
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

        result = OpticalDelayLineHomeParams()
        result["home_direction"] = params.home_direction
        result["limit_switch"] = params.limit_switch
        result["home_velocity"] = params.home_velocity * pnpq_ureg.kbd101_velocity
        result["offset_distance"] = params.offset_distance * pnpq_ureg.kbd101_position

        return result

    def set_homeparams(
        self,
        home_direction: None | HomeDirection = None,
        limit_switch: None | LimitSwitch = None,
        home_velocity: None | Quantity = None,
        offset_distance: None | Quantity = None,
    ) -> None:
        # First get the current velocity parameters
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
                .to(pnpq_ureg.kbd101_velocity)
                .magnitude,
                offset_distance=params["offset_distance"]
                .to(pnpq_ureg.kbd101_position)
                .magnitude,
            )
        )

    def get_jogparams(self) -> OpticalDelayLineJogParams:
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

        result = OpticalDelayLineJogParams()
        result["jog_mode"] = params.jog_mode
        result["jog_step_size"] = params.jog_step_size * pnpq_ureg.kbd101_position
        result["jog_minimum_velocity"] = (
            params.jog_minimum_velocity * pnpq_ureg.kbd101_velocity
        )
        result["jog_acceleration"] = (
            params.jog_acceleration * pnpq_ureg.kbd101_acceleration
        )
        result["jog_maximum_velocity"] = (
            params.jog_maximum_velocity * pnpq_ureg.kbd101_velocity
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
                .to(pnpq_ureg.kbd101_position)
                .magnitude,
                jog_minimum_velocity=params["jog_minimum_velocity"]
                .to(pnpq_ureg.kbd101_velocity)
                .magnitude,
                jog_acceleration=params["jog_acceleration"]
                .to(pnpq_ureg.kbd101_acceleration)
                .magnitude,
                jog_maximum_velocity=params["jog_maximum_velocity"]
                .to(pnpq_ureg.kbd101_velocity)
                .magnitude,
                jog_stop_mode=params["jog_stop_mode"],
            )
        )
        self.log.debug("set_jogparams", params=params)

    def _poller(self) -> None:
        """Intended to be run in a background thread.

        Constantly send ``ACK_USTATUSUPDATE`` messages to keep the
        connection alive; some parts of the official manual suggest
        that if this ``ACK`` message is not sent at regular intervals,
        the device will assume the connection is closed and stop
        responding to commands.

        Generally speaking, this thread will always exit with an
        exception of some kind; the exception is only logged at debug
        level to avoid cluttering the log, but if status update
        messages are mysteriously failing to appear, this is a good
        place to start.

        """
        try:
            while True:
                time.sleep(0.9)
                self.connection.send_message_unordered(
                    AptMessage_MGMSG_MOT_ACK_USTATUSUPDATE(
                        destination=Address.GENERIC_USB,
                        source=Address.HOST_CONTROLLER,
                    )
                )
        except BaseException as e:  # pylint: disable=W0718
            self.log.debug(event=Event.APT_POLLER_EXIT, exc_info=e)
