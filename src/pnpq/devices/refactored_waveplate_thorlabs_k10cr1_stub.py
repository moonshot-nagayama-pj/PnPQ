from dataclasses import dataclass, field
from typing import cast

import structlog
from pint import Quantity

from pnpq.devices.refactored_waveplate_thorlabs_k10cr1 import (
    AbstractWaveplateThorlabsK10CR1,
)

from ..apt.protocol import Address, AptMessage_MGMSG_MOT_GET_VELPARAMS, ChanIdent
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

    # TODO: Add K10CR1 parameters
    # current_params = None

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

    def move_absolute(self, position: Quantity) -> None:
        # Convert distance to K1CR10 steps
        # TODO: Check if input is too large or too small for the device
        position_in_steps = position.to("k10cr1_step")
        self.current_state[self._chan_ident] = cast(Quantity, position_in_steps)

        self.log.info(f"[Waveplate Stub] Channel {self._chan_ident} move to {position}")

    def get_velparams(self) -> AptMessage_MGMSG_MOT_GET_VELPARAMS:
        return AptMessage_MGMSG_MOT_GET_VELPARAMS(
            destination=Address.HOST_CONTROLLER,
            source=Address.GENERIC_USB,
            chan_ident=self._chan_ident,
            minimum_velocity=0,
            acceleration=1,
            maximum_velocity=2, # Not sure what to put here

        )
