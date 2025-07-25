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
from pnpq.stub_util import sleep_delta_position

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

    time_scaling_factor: float = field(default=0.0)  # Simulate time if > 0.0

    current_velocity_params: WaveplateVelocityParams = field(
        default_factory=WaveplateVelocityParams
    )
    current_jog_params: WaveplateJogParams = field(default_factory=WaveplateJogParams)
    current_home_params: WaveplateHomeParams = field(
        default_factory=WaveplateHomeParams
    )
    homed: bool = field(default=False, init=False)

    current_state: dict[ChanIdent, Quantity] = field(init=False)

    def __post_init__(self) -> None:
        self.log.info("[Waveplate Stub] Initialized")

        if self.time_scaling_factor < 0.0:
            raise ValueError("Time multiplier must be greater than or equal to 0.0.")

        object.__setattr__(
            self,
            "current_state",
            {
                self._chan_ident: 0 * pnpq_ureg.k10cr1_step,
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

        delta_position = cast(
            Quantity, position_in_steps - self.current_state[self._chan_ident]
        )
        sleep_delta_position(
            self.time_scaling_factor,
            self.get_velparams()["maximum_velocity"],
            delta_position,
        )  # NOTE: Should it be maximum_velocity or minimum_velocity? Or something in between?

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
        self.current_velocity_params["minimum_velocity"] = minimum_velocity
        self.current_velocity_params["acceleration"] = acceleration
        self.current_velocity_params["maximum_velocity"] = maximum_velocity

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

        self.current_jog_params["jog_mode"] = jog_mode
        self.current_jog_params["jog_step_size"] = jog_step_size
        self.current_jog_params["jog_minimum_velocity"] = jog_minimum_velocity
        self.current_jog_params["jog_acceleration"] = jog_acceleration
        self.current_jog_params["jog_maximum_velocity"] = jog_maximum_velocity
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
        self.current_home_params["home_direction"] = home_direction
        self.current_home_params["limit_switch"] = limit_switch
        self.current_home_params["home_velocity"] = home_velocity
        self.current_home_params["offset_distance"] = offset_distance

        # TODO: Remove f string
        self.log.info(f"[K10CR1 Stub] Updated parameters: {self.current_home_params}")

    def jog(self, jog_direction: JogDirection) -> None:

        jog_value = self.current_jog_params["jog_step_size"]
        current_value = self.current_state[self._chan_ident].to("k10cr1_step").magnitude
        jog_value_magnitude = jog_value.to("k10cr1_step").magnitude

        sleep_delta_position(
            self.time_scaling_factor,
            self.current_jog_params["jog_maximum_velocity"],
            jog_value,
        )

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

        home_value = 0 * pnpq_ureg.k10cr1_step

        delta_position: Quantity = self.current_state[self._chan_ident] - home_value
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

        self.current_state[self._chan_ident] = home_value

        # TODO: Remove f string
        self.log.info(f"[Waveplate Stub] Channel {self._chan_ident} home")

    def is_homed(self) -> bool:
        return self.homed

    def identify(self) -> None:
        # Do nothing for the stub
        pass
