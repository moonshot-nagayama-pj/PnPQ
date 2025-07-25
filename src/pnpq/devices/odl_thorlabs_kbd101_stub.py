from dataclasses import dataclass, field
from typing import cast

import structlog
from pint import Quantity

from pnpq.apt.protocol import AptMessage_MGMSG_MOT_GET_USTATUSUPDATE
from pnpq.stub_util import sleep_delta_position

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
from .odl_thorlabs_kbd101 import (
    AbstractOpticalDelayLineThorlabsKBD101,
    OpticalDelayLineHomeParams,
    OpticalDelayLineJogParams,
    OpticalDelayLineVelocityParams,
)


@dataclass(frozen=True, kw_only=True)
class OpticalDelayLineThorlabsKBD101Stub(AbstractOpticalDelayLineThorlabsKBD101):
    _chan_ident = ChanIdent.CHANNEL_1

    time_scaling_factor: float = field(default=0.0)  # Simulate time if > 0.0

    log = structlog.get_logger()

    current_velocity_params: OpticalDelayLineVelocityParams = field(
        default_factory=OpticalDelayLineVelocityParams
    )
    current_home_params: OpticalDelayLineHomeParams = field(
        default_factory=OpticalDelayLineHomeParams
    )
    current_jog_params: OpticalDelayLineJogParams = field(
        default_factory=OpticalDelayLineJogParams
    )

    current_state: dict[ChanIdent, Quantity] = field(init=False)

    def __post_init__(self) -> None:
        self.log.info("[KBD101 Stub] Initialized")

        if self.time_scaling_factor < 0.0:
            raise ValueError("Time multiplier must be greater than or equal to 0.0.")

        object.__setattr__(
            self,
            "current_state",
            {
                ChanIdent.CHANNEL_1: 0 * pnpq_ureg.kbd101_position,
            },
        )

    def identify(self) -> None:
        self.log.info("[KBD101 Stub] Identify")

    def home(self) -> None:
        home_position = 0 * pnpq_ureg.kbd101_position
        delta_position: Quantity = self.current_state[self._chan_ident] - home_position

        sleep_delta_position(
            self.time_scaling_factor,
            self.current_home_params["home_velocity"],
            delta_position,
        )

        object.__setattr__(
            self,
            "homed",
            True,
        )

        self.current_state[self._chan_ident] = home_position

        # TODO: Remove f string
        self.log.info(f"[KBD101 Stub] Channel {self._chan_ident} home")

    def move_absolute(self, position: Quantity) -> None:
        # TODO: Check if input is too large or too small for the device
        position_in_steps = position.to("kbd101_position")

        delta_position = cast(
            Quantity, position_in_steps - self.current_state[self._chan_ident]
        )

        sleep_delta_position(
            self.time_scaling_factor,
            self.get_velparams()["maximum_velocity"],
            delta_position,
        )  # TODO: Should it be maximum_velocity or minimum_velocity? Or something in between?

        self.current_state[self._chan_ident] = cast(Quantity, position_in_steps)

        self.log.info("[KBD101 Stub] Channel %s move to %s", self._chan_ident, position)

    def jog(self, jog_direction: JogDirection) -> None:
        jog_value = self.current_jog_params["jog_step_size"]
        jog_value_magnitude = jog_value.to("kbd101_position").magnitude
        current_value = (
            self.current_state[self._chan_ident].to("kbd101_position").magnitude
        )

        sleep_delta_position(
            self.time_scaling_factor,
            self.current_jog_params["jog_maximum_velocity"],
            jog_value,
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

        self.current_velocity_params["minimum_velocity"] = minimum_velocity
        self.current_velocity_params["acceleration"] = acceleration
        self.current_velocity_params["maximum_velocity"] = maximum_velocity

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
        self.current_home_params["home_direction"] = home_direction
        self.current_home_params["limit_switch"] = limit_switch
        self.current_home_params["home_velocity"] = home_velocity
        self.current_home_params["offset_distance"] = offset_distance

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
        self.current_jog_params["jog_mode"] = jog_mode
        self.current_jog_params["jog_step_size"] = jog_step_size
        self.current_jog_params["jog_minimum_velocity"] = jog_minimum_velocity
        self.current_jog_params["jog_acceleration"] = jog_acceleration
        self.current_jog_params["jog_maximum_velocity"] = jog_maximum_velocity
        self.current_jog_params["jog_stop_mode"] = jog_stop_mode

        self.log.info("[KBD101 Stub] Updated parameters: %s", self.current_jog_params)
