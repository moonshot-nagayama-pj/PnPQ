from dataclasses import dataclass, field
from typing import cast

import structlog
from pint import Quantity

from pnpq.devices.waveplate_thorlabs_k10cr1 import (
    AbstractWaveplateThorlabsK10CR1,
    WaveplateHomeParams,
    WaveplateJogParams,
    WaveplateVelocityParams,
)

from ..apt.protocol import (
    ChanIdent,
    HomeDirection,
    JogDirection,
    JogMode,
    LimitSwitch,
    StopMode,
)
from ..units import pnpq_ureg


@dataclass(frozen=True, kw_only=True)
class WaveplateThorlabsK10CR1Stub(AbstractWaveplateThorlabsK10CR1):
    _chan_ident = ChanIdent.CHANNEL_1

    log = structlog.get_logger()

    current_velocity_params: WaveplateVelocityParams = field(init=False)
    current_jog_params: WaveplateJogParams = field(init=False)
    current_home_params: WaveplateHomeParams = field(init=False)
    homed: bool = field(default=False, init=False)

    current_state: dict[ChanIdent, Quantity] = field(init=False)

    def __post_init__(self) -> None:
        self.log.info("[Waveplate Stub] Initialized")

        object.__setattr__(
            self,
            "current_state",
            {
                self._chan_ident: 0 * pnpq_ureg.k10cr1_step,
            },
        )

        object.__setattr__(
            self,
            "current_velocity_params",
            {
                "minimum_velocity": 0 * pnpq_ureg.k10cr1_velocity,
                "acceleration": 0 * pnpq_ureg.k10cr1_acceleration,
                "maximum_velocity": 10
                * pnpq_ureg.k10cr1_velocity,  # Default value set to 10 k10cr1_velocity based on expected operational range
            },
        )

        object.__setattr__(
            self,
            "current_jog_params",
            {
                "jog_mode": JogMode.SINGLE_STEP,
                "jog_step_size": 10 * pnpq_ureg.k10cr1_step,
                "jog_minimum_velocity": 0 * pnpq_ureg.k10cr1_velocity,
                "jog_acceleration": 0 * pnpq_ureg.k10cr1_acceleration,
                "jog_maximum_velocity": 10
                * pnpq_ureg.k10cr1_velocity,  # Default value set to 10 k10cr1_velocity based on expected operational range
                "jog_stop_mode": StopMode.IMMEDIATE,
            },
        )

        object.__setattr__(
            self,
            "current_home_params",
            {
                "home_direction": HomeDirection.FORWARD_0,
                "limit_switch": LimitSwitch.HARDWARE_FORWARD,
                "home_velocity": 0 * pnpq_ureg.k10cr1_velocity,
                "offset_distance": 0 * pnpq_ureg.k10cr1_step,
            },
        )

        object.__setattr__(
            self,
            "homed",
            True,
        )

    def move_absolute(self, position: Quantity) -> None:
        # Convert distance to K1CR10 steps
        # TODO: Check if input is too large or too small for the device
        position_in_steps = position.to("k10cr1_step")
        self.current_state[self._chan_ident] = cast(Quantity, position_in_steps)

        self.log.info(
            "[Waveplate Stub] Channel %s move to %s", self._chan_ident, position
        )

    def get_velparams(self) -> WaveplateVelocityParams:
        return self.current_velocity_params

    def set_velparams(
        self,
        minimum_velocity: None | Quantity = None,
        acceleration: None | Quantity = None,
        maximum_velocity: None | Quantity = None,
    ) -> None:

        if minimum_velocity is not None:
            self.current_velocity_params["minimum_velocity"] = cast(
                Quantity, minimum_velocity.to("k10cr1_velocity")
            )
        if acceleration is not None:
            self.current_velocity_params["acceleration"] = cast(
                Quantity, acceleration.to("k10cr1_acceleration")
            )
        if maximum_velocity is not None:
            self.current_velocity_params["maximum_velocity"] = cast(
                Quantity, maximum_velocity.to("k10cr1_velocity")
            )
        self.log.info(
            "[K10CR1 Stub] Updated parameters: %s", self.current_velocity_params
        )

    def get_jogparams(self) -> WaveplateJogParams:
        return self.current_jog_params

    def set_jogparams(
        self,
        jog_mode: None | JogMode = None,
        jog_step_size: None | Quantity = None,
        jog_minimum_velocity: None | Quantity = None,
        jog_acceleration: None | Quantity = None,
        jog_maximum_velocity: None | Quantity = None,
        jog_stop_mode: None | StopMode = None,
    ) -> None:
        # There has to be a better way to do this...
        if jog_mode is not None:
            self.current_jog_params["jog_mode"] = jog_mode

        if jog_step_size is not None:
            self.current_jog_params["jog_step_size"] = cast(
                Quantity, jog_step_size.to("k10cr1_step")
            )
        if jog_minimum_velocity is not None:
            self.current_jog_params["jog_minimum_velocity"] = cast(
                Quantity, jog_minimum_velocity.to("k10cr1_velocity")
            )
        if jog_acceleration is not None:
            self.current_jog_params["jog_acceleration"] = cast(
                Quantity, jog_acceleration.to("k10cr1_acceleration")
            )
        if jog_maximum_velocity is not None:
            self.current_jog_params["jog_maximum_velocity"] = cast(
                Quantity, jog_maximum_velocity.to("k10cr1_velocity")
            )
        if jog_stop_mode is not None:
            self.current_jog_params["jog_stop_mode"] = jog_stop_mode

        # TODO: Remove f string
        self.log.info(f"[K10CR1 Stub] Updated parameters: {self.current_jog_params}")

    def get_homeparams(self) -> WaveplateHomeParams:
        return self.current_home_params

    def set_homeparams(
        self,
        home_direction: None | HomeDirection = None,
        limit_switch: None | LimitSwitch = None,
        home_velocity: None | Quantity = None,
        offset_distance: None | Quantity = None,
    ) -> None:
        if home_direction is not None:
            self.current_home_params["home_direction"] = home_direction
        if limit_switch is not None:
            self.current_home_params["limit_switch"] = limit_switch
        if home_velocity is not None:
            self.current_home_params["home_velocity"] = cast(
                Quantity, home_velocity.to("k10cr1_velocity")
            )
        if offset_distance is not None:
            self.current_home_params["offset_distance"] = cast(
                Quantity, offset_distance.to("k10cr1_step")
            )

        # TODO: Remove f string
        self.log.info(f"[K10CR1 Stub] Updated parameters: {self.current_home_params}")

    def jog(self, jog_direction: JogDirection) -> None:

        jog_value = self.current_jog_params["jog_step_size"]
        current_value = self.current_state[self._chan_ident].to("k10cr1_step").magnitude
        jog_value_magnitude = jog_value.to("k10cr1_step").magnitude

        if jog_direction == JogDirection.FORWARD:
            new_value_magnitude = current_value + jog_value_magnitude
        else:  # Reverse
            new_value_magnitude = current_value - jog_value_magnitude

        new_value = new_value_magnitude * pnpq_ureg.k10cr1_step
        self.current_state[self._chan_ident] = new_value

        self.log.info(
            f"[Waveplate Stub] Channel {self._chan_ident} jog {jog_direction}"
        )

    def home(self) -> None:
        object.__setattr__(
            self,
            "homed",
            True,
        )
        self.current_state[self._chan_ident] = 0 * pnpq_ureg.k10cr1_step

        # TODO: Remove f string
        self.log.info(f"[Waveplate Stub] Channel {self._chan_ident} home")

    def is_homed(self) -> bool:
        return self.homed

    def identify(self) -> None:
        # Do nothing for the stub
        pass
