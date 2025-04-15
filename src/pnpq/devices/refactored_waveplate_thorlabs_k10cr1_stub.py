from dataclasses import dataclass, field
from typing import cast

import structlog
from pint import Quantity

from pnpq.devices.refactored_waveplate_thorlabs_k10cr1 import (
    AbstractWaveplateThorlabsK10CR1,
    WaveplateVelocityParams,
)

from ..apt.protocol import ChanIdent
from ..units import pnpq_ureg


@dataclass(frozen=True, kw_only=True)
class WaveplateThorlabsK10CR1Stub(AbstractWaveplateThorlabsK10CR1):
    log = structlog.get_logger()

    # Setup channels for the device
    available_channels: frozenset[ChanIdent] = frozenset(
        [
            ChanIdent.CHANNEL_1,
        ]
    )

    current_params: WaveplateVelocityParams = field(init=False)

    current_state: dict[ChanIdent, Quantity] = field(init=False)

    def __post_init__(self) -> None:
        self.log.info("[Waveplate Stub] Initialized")

        object.__setattr__(
            self,
            "current_state",
            {
                ChanIdent.CHANNEL_1: 0 * pnpq_ureg.k10cr1_step,
            },
        )

        object.__setattr__(
            self,
            "current_params",
            {
                "minimum_velocity": 0 * pnpq_ureg.k10cr1_velocity,
                "acceleration": 0 * pnpq_ureg.k10cr1_acceleration,
                "maximum_velocity": 0
                * pnpq_ureg.k10cr1_velocity,  # TODO: Search for appropriate initial values
            },
        )

    def move_absolute(self, position: Quantity) -> None:
        # Convert distance to K1CR10 steps
        # TODO: Check if input is too large or too small for the device
        position_in_steps = position.to("k10cr1_step")
        self.current_state[self._chan_ident] = cast(Quantity, position_in_steps)

        self.log.info(f"[Waveplate Stub] Channel {self._chan_ident} move to {position}")

    def get_velparams(self) -> WaveplateVelocityParams:
        return self.current_params

    def set_velparams(
        self,
        minimum_velocity: None | Quantity = None,
        acceleration: None | Quantity = None,
        maximum_velocity: None | Quantity = None,
    ) -> None:

        if minimum_velocity is not None:
            self.current_params["minimum_velocity"] = cast(
                Quantity, minimum_velocity.to("k10cr1_velocity")
            )
        if acceleration is not None:
            self.current_params["acceleration"] = cast(
                Quantity, acceleration.to("k10cr1_acceleration")
            )
        if maximum_velocity is not None:
            self.current_params["maximum_velocity"] = cast(
                Quantity, maximum_velocity.to("k10cr1_velocity")
            )
        self.log.info(f"[K10CR1 Stub] Updated parameters: {self.current_params}")
