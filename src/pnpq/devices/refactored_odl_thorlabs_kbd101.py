import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TypedDict, cast

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
from ..units import pnpq_ureg


# TODO: This is set as a separate class for now.
# If the Thorlabs waveplates use exactly the same logic, we might be able to combine them
class OpticalDelayLineVelocityParams(TypedDict):
    """TypedDict for ODL velocity parameters.
    Used in `get_velparams` method.
    """

    #: Dimensionality must be ([length] / [time]) or kbd101_velocity
    minimum_velocity: Quantity
    #: Dimensionality must be ([length] / [time] ** 2) or kbd101_acceleration
    acceleration: Quantity
    #: Dimensionality must be ([length] / [time]) or kbd101_velocity
    maximum_velocity: Quantity


class OpticalDelayLineJogParams(TypedDict):
    """TypedDict for optical delay line jog parameters.
    Used in the `get_jogparams` method.
    """

    #: Jog mode can be continuous jogging or single step jogging.
    jog_mode: JogMode
    #: Dimensionality must be [length] or kbd101_position
    jog_step_size: Quantity
    #: Dimensionality must be ([length] / [time]) or kbd101_velocity
    jog_minimum_velocity: Quantity
    #: Dimensionality must be ([length] / [time] ** 2) or kbd101_acceleration
    jog_acceleration: Quantity
    #: Dimensionality must be ([length] / [time]) or kbd101_velocity
    jog_maximum_velocity: Quantity
    #: Stop mode can be immediate (abrupt) stop or profiled stop (with controlled deceleration)
    jog_stop_mode: StopMode


class OpticalDelayLineHomeParams(TypedDict):
    """TypedDict for ODL home parameters.
    Used in the `get_homeparams` method.
    """

    # The direction to move while homing. For ODLs, this value is always positive (forward).
    home_direction: HomeDirection
    #: The limit switch associated with the home position
    limit_switch: LimitSwitch
    #: Dimensionality must be ([length] / time) or kbd101_velocity
    home_velocity: Quantity
    #: Dimensionality must be [length] or kbd101_position
    offset_distance: Quantity


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

        result: OpticalDelayLineVelocityParams = {
            "minimum_velocity": params.minimum_velocity * pnpq_ureg.kbd101_velocity,
            "acceleration": params.acceleration * pnpq_ureg.kbd101_acceleration,
            "maximum_velocity": params.maximum_velocity * pnpq_ureg.kbd101_velocity,
        }
        return result

    def set_velparams(
        self,
        minimum_velocity: None | Quantity = None,
        acceleration: None | Quantity = None,
        maximum_velocity: None | Quantity = None,
    ) -> None:

        # First get the current velocity parameters
        params = self.get_velparams()

        if minimum_velocity is not None:
            params["minimum_velocity"] = cast(
                Quantity, minimum_velocity.to("kbd101_velocity")
            )
        if acceleration is not None:
            params["acceleration"] = cast(
                Quantity, acceleration.to("kbd101_acceleration")
            )
        if maximum_velocity is not None:
            params["maximum_velocity"] = cast(
                Quantity, maximum_velocity.to("kbd101_velocity")
            )

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

        result: OpticalDelayLineHomeParams = {
            "home_direction": HomeDirection(params.home_direction),
            "limit_switch": LimitSwitch(params.limit_switch),
            "home_velocity": params.home_velocity * pnpq_ureg.kbd101_velocity,
            "offset_distance": params.offset_distance * pnpq_ureg.kbd101_position,
        }
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

        if home_direction is not None:
            params["home_direction"] = home_direction

        if limit_switch is not None:
            params["limit_switch"] = limit_switch

        if home_velocity is not None:
            params["home_velocity"] = home_velocity

        if offset_distance is not None:
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

        result: OpticalDelayLineJogParams = {
            "jog_mode": params.jog_mode,
            "jog_step_size": params.jog_step_size * pnpq_ureg.kbd101_position,
            "jog_minimum_velocity": params.jog_minimum_velocity
            * pnpq_ureg.kbd101_velocity,
            "jog_acceleration": params.jog_acceleration * pnpq_ureg.kbd101_acceleration,
            "jog_maximum_velocity": params.jog_maximum_velocity
            * pnpq_ureg.kbd101_velocity,
            "jog_stop_mode": params.jog_stop_mode,
        }
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

        if jog_mode is not None:
            params["jog_mode"] = jog_mode
        if jog_step_size is not None:
            params["jog_step_size"] = jog_step_size
        if jog_minimum_velocity is not None:
            params["jog_minimum_velocity"] = jog_minimum_velocity
        if jog_acceleration is not None:
            params["jog_acceleration"] = jog_acceleration
        if jog_maximum_velocity is not None:
            params["jog_maximum_velocity"] = jog_maximum_velocity
        if jog_stop_mode is not None:
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
