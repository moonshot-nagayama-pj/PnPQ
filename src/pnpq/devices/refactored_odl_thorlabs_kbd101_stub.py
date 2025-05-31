from dataclasses import dataclass, field
from typing import cast

import structlog
from pint import Quantity

from pnpq.apt.protocol import AptMessage_MGMSG_MOT_GET_USTATUSUPDATE

from ..apt.protocol import (
    Address,
    ChanIdent,
    HomeDirection,
    JogDirection,
    JogMode,
    LimitSwitch,
    StopMode,
    UStatus,
    UStatusBits,
)
from ..units import pnpq_ureg
from .refactored_odl_thorlabs_kbd101 import (
    AbstractOpticalDelayLineThorlabsKBD101,
    OpticalDelayLineHomeParams,
    OpticalDelayLineJogParams,
    OpticalDelayLineVelocityParams,
)


@dataclass(frozen=True, kw_only=True)
class OpticalDelayLineThorlabsKBD101Stub(AbstractOpticalDelayLineThorlabsKBD101):
    _chan_ident = ChanIdent.CHANNEL_1

    log = structlog.get_logger()

    # Setup channels for the device
    available_channels: frozenset[ChanIdent] = frozenset(
        [
            ChanIdent.CHANNEL_1,
        ]
    )

    current_velocity_params: OpticalDelayLineVelocityParams = field(init=False)
    current_home_params: OpticalDelayLineHomeParams = field(init=False)
    current_jog_params: OpticalDelayLineJogParams = field(init=False)

    current_state: dict[ChanIdent, Quantity] = field(init=False)

    def __post_init__(self) -> None:
        self.log.info("[KBD101 Stub] Initialized")

        object.__setattr__(
            self,
            "current_state",
            {
                ChanIdent.CHANNEL_1: 0 * pnpq_ureg.kbd101_position,
            },
        )

        object.__setattr__(
            self,
            "current_velocity_params",
            {
                "minimum_velocity": 0 * pnpq_ureg.kbd101_velocity,
                "acceleration": 0 * pnpq_ureg.kbd101_acceleration,
                "maximum_velocity": 10 * pnpq_ureg.kbd101_velocity,
            },
        )

        object.__setattr__(
            self,
            "current_home_params",
            {
                "home_direction": HomeDirection.FORWARD,
                "limit_switch": LimitSwitch.HARDWARE_FORWARD,
                "home_velocity": 134218 * pnpq_ureg.kbd101_velocity,
                "offset_distance": 0 * pnpq_ureg.kbd101_position,
            },
        )

        object.__setattr__(
            self,
            "current_jog_params",
            {
                "jog_mode": JogMode.SINGLE_STEP,
                "jog_step_size": 20000 * pnpq_ureg.kbd101_position,
                "jog_minimum_velocity": 134218 * pnpq_ureg.kbd101_velocity,
                "jog_acceleration": 7 * pnpq_ureg.kbd101_acceleration,
                "jog_maximum_velocity": 134218 * pnpq_ureg.kbd101_velocity,
                "jog_stop_mode": StopMode.CONTROLLED,
            },
        )

    def identify(self) -> None:
        self.log.info("[KBD101 Stub] Identify")

    def home(self) -> None:
        home_position = 0 * pnpq_ureg.kbd101_position
        self.log.info("[KBD101 Stub] Channel %s home", self._chan_ident)

        self.move_absolute(home_position)

    def move_absolute(self, position: Quantity) -> None:
        # TODO: Check if input is too large or too small for the device
        kbd101_position = position.to("kbd101_position")
        self.current_state[self._chan_ident] = cast(Quantity, kbd101_position)

        self.log.info(
            "[KBD101 Stub] Channel %s move to %s", self._chan_ident, kbd101_position
        )

    def jog(self, jog_direction: JogDirection) -> None:
        jog_value = self.current_jog_params["jog_step_size"]
        jog_value_magnitude = jog_value.to("kbd101_position").magnitude
        current_value = (
            self.current_state[self._chan_ident].to("kbd101_position").magnitude
        )

        if jog_direction == JogDirection.FORWARD:
            new_value_magnitude = current_value + jog_value_magnitude
        else:  # Reverse
            new_value_magnitude = current_value - jog_value_magnitude

        new_value = new_value_magnitude * pnpq_ureg.kbd101_position
        self.current_state[self._chan_ident] = cast(Quantity, new_value)

        self.log.info(
            "[KBD101 Stub] Channel %s jog %s to %s",
            self._chan_ident,
            jog_direction,
            new_value,
        )

    def get_status(self) -> AptMessage_MGMSG_MOT_GET_USTATUSUPDATE:
        msg = AptMessage_MGMSG_MOT_GET_USTATUSUPDATE(
            chan_ident=self._chan_ident,
            position=self.current_state[self._chan_ident].magnitude,
            velocity=self.current_velocity_params["maximum_velocity"].magnitude,
            motor_current=3 * pnpq_ureg.milliamp,
            status=UStatus.from_bits(UStatusBits.ACTIVE),
            destination=Address.HOST_CONTROLLER,
            source=Address.GENERIC_USB,
        )
        return msg

    def get_velparams(self) -> OpticalDelayLineVelocityParams:
        return self.current_velocity_params

    def set_velparams(
        self,
        minimum_velocity: None | Quantity = None,
        acceleration: None | Quantity = None,
        maximum_velocity: None | Quantity = None,
    ) -> None:

        if minimum_velocity is not None:
            self.current_velocity_params["minimum_velocity"] = cast(
                Quantity, minimum_velocity.to("kbd101_velocity")
            )
        if acceleration is not None:
            self.current_velocity_params["acceleration"] = cast(
                Quantity, acceleration.to("kbd101_acceleration")
            )
        if maximum_velocity is not None:
            self.current_velocity_params["maximum_velocity"] = cast(
                Quantity, maximum_velocity.to("kbd101_velocity")
            )
        self.log.info(
            "[KBD101 Stub] Updated parameters: %s", self.current_velocity_params
        )

    def get_homeparams(self) -> OpticalDelayLineHomeParams:
        return self.current_home_params

    def set_homeparams(
        self,
        home_direction: HomeDirection | None = None,
        limit_switch: LimitSwitch | None = None,
        home_velocity: Quantity | None = None,
        offset_distance: Quantity | None = None,
    ) -> None:
        if home_direction is not None:
            self.current_home_params["home_direction"] = home_direction
        if limit_switch is not None:
            self.current_home_params["limit_switch"] = limit_switch
        if home_velocity is not None:
            self.current_home_params["home_velocity"] = cast(
                Quantity, home_velocity.to("kbd101_velocity")
            )
        if offset_distance is not None:
            self.current_home_params["offset_distance"] = cast(
                Quantity, offset_distance.to("kbd101_position")
            )
        self.log.info("[KBD101 Stub] Updated parameters: %s", self.current_home_params)

    def get_jogparams(self) -> OpticalDelayLineJogParams:
        return self.current_jog_params

    def set_jogparams(
        self,
        jog_mode: JogMode | None = None,
        jog_step_size: Quantity | None = None,
        jog_minimum_velocity: Quantity | None = None,
        jog_acceleration: Quantity | None = None,
        jog_maximum_velocity: Quantity | None = None,
        jog_stop_mode: StopMode | None = None,
    ) -> None:
        if jog_mode is not None:
            self.current_jog_params["jog_mode"] = jog_mode
        if jog_step_size is not None:
            self.current_jog_params["jog_step_size"] = cast(
                Quantity, jog_step_size.to("kbd101_position")
            )
        if jog_minimum_velocity is not None:
            self.current_jog_params["jog_minimum_velocity"] = cast(
                Quantity, jog_minimum_velocity.to("kbd101_velocity")
            )
        if jog_acceleration is not None:
            self.current_jog_params["jog_acceleration"] = cast(
                Quantity, jog_acceleration.to("kbd101_acceleration")
            )
        if jog_maximum_velocity is not None:
            self.current_jog_params["jog_maximum_velocity"] = cast(
                Quantity, jog_maximum_velocity.to("kbd101_velocity")
            )
        if jog_stop_mode is not None:
            self.current_jog_params["jog_stop_mode"] = jog_stop_mode

        self.log.info("[KBD101 Stub] Updated parameters: %s", self.current_jog_params)
