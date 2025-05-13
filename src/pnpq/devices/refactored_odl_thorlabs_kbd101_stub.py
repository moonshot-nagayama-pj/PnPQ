from dataclasses import dataclass, field
from typing import cast

import structlog
from pint import Quantity
from ..apt.protocol import (
    ChanIdent,
)
from ..units import pnpq_ureg

from .refactored_odl_thorlabs_kbd101 import (OpticalDelayLineVelocityParams, AbstractOpticalDelayLineThorlabsKBD101)

@dataclass(frozen=True, kw_only=True)
class OpticalDelayLineThorlabsKBD101Stub(AbstractOpticalDelayLineThorlabsKBD101):
    log = structlog.get_logger()

    # Setup channels for the device
    available_channels: frozenset[ChanIdent] = frozenset(
        [
            ChanIdent.CHANNEL_1,
        ]
    )

    current_velocity_params: OpticalDelayLineVelocityParams = field(init=False)

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

    def identify(self) -> None:
        self.log.info(f"[KBD101 Stub] Identify")

    def home(self) -> None:
        # TODO: Update when set home params are implemented
        home_position = 0 * pnpq_ureg.kbd101_step
        self.log.info(f"[KBD101 Stub] Channel {self._chan_ident} home")

        self.move_absolute(home_position)

    def move_absolute(self, position: Quantity) -> None:
        # TODO: Check if input is too large or too small for the device
        kbd101_position = position.to("kbd101_position")
        self.current_state[self._chan_ident] = cast(Quantity, kbd101_position)

        self.log.info(f"[Waveplate Stub] Channel {self._chan_ident} move to {kbd101_position}")

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
            f"[KBD101 Stub] Updated parameters: {self.current_velocity_params}"
        )
