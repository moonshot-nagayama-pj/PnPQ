from dataclasses import dataclass, field
from typing import cast

import structlog
from pint import Quantity

from pnpq.apt.protocol import Address, UStatus, UStatusBits
from pnpq.stub_util import sleep_delta_position

from ..apt.protocol import (
    AptMessage_MGMSG_MOT_GET_USTATUSUPDATE,
    ChanIdent,
    JogDirection,
)
from ..units import pnpq_ureg
from .polarization_controller_thorlabs_mpc import (
    AbstractPolarizationControllerThorlabsMPC,
    PolarizationControllerParams,
)


@dataclass(frozen=True, kw_only=True)
class PolarizationControllerThorlabsMPC320Stub(
    AbstractPolarizationControllerThorlabsMPC
):
    log = structlog.get_logger()

    time_scaling_factor: float = field(default=0.0)  # Simulate time if > 0.0

    # Setup channels for the device
    available_channels: frozenset[ChanIdent] = frozenset(
        [
            ChanIdent.CHANNEL_1,
            ChanIdent.CHANNEL_2,
            ChanIdent.CHANNEL_3,
        ]
    )

    current_params: PolarizationControllerParams = field(
        default_factory=PolarizationControllerParams
    )

    current_state: dict[ChanIdent, Quantity] = field(init=False)

    def __post_init__(self) -> None:
        self.log.info("[MPC Stub] Initialized")

        if self.time_scaling_factor < 0.0:
            raise ValueError("Time multiplier must be greater than or equal to 0.0.")

        # Current params will be set to a default state
        # To change them, use the set_params method

        object.__setattr__(
            self,
            "current_state",
            {
                ChanIdent.CHANNEL_1: 0 * pnpq_ureg.mpc320_steps,
                ChanIdent.CHANNEL_2: 0 * pnpq_ureg.mpc320_steps,
                ChanIdent.CHANNEL_3: 0 * pnpq_ureg.mpc320_steps,
            },
        )

    def home(self, chan_ident: ChanIdent) -> None:
        home_value = self.current_params["home_position"]

        delta_position: Quantity = self.current_state[chan_ident] - home_value
        sleep_delta_position(
            self.time_scaling_factor, self.current_params["velocity"], delta_position
        )

        self.current_state[chan_ident] = home_value
        self.log.info(f"[MPC Stub] Channel {chan_ident} home")

    def identify(self, chan_ident: ChanIdent) -> None:
        self.log.info(f"[MPC Stub] Channel {chan_ident} identify")

    def get_status(
        self, chan_ident: ChanIdent
    ) -> AptMessage_MGMSG_MOT_GET_USTATUSUPDATE:
        msg = AptMessage_MGMSG_MOT_GET_USTATUSUPDATE(
            chan_ident=chan_ident,
            position=self.current_state[chan_ident].magnitude,
            velocity=self.current_params["velocity"].magnitude,
            motor_current=3 * pnpq_ureg.milliamp,
            status=UStatus.from_bits(UStatusBits.ACTIVE),
            destination=Address.HOST_CONTROLLER,
            source=Address.GENERIC_USB,
        )
        return msg

    def get_status_all(self) -> tuple[AptMessage_MGMSG_MOT_GET_USTATUSUPDATE, ...]:
        all_status = []
        for channel in self.available_channels:
            status = self.get_status(channel)
            all_status.append(status)
        return tuple(all_status)

    def jog(self, chan_ident: ChanIdent, jog_direction: JogDirection) -> None:
        # Use match to get jog step for requested channel
        match chan_ident:
            case ChanIdent.CHANNEL_1:
                jog_value = self.current_params["jog_step_1"]
            case ChanIdent.CHANNEL_2:
                jog_value = self.current_params["jog_step_2"]
            case ChanIdent.CHANNEL_3:
                jog_value = self.current_params["jog_step_3"]

        current_value = self.current_state[chan_ident].to("mpc320_steps").magnitude
        jog_value_magnitude = jog_value.to("mpc320_steps").magnitude

        if jog_direction == JogDirection.FORWARD:
            new_value_magnitude = current_value + jog_value_magnitude
        else:  # Reverse
            new_value_magnitude = current_value - jog_value_magnitude

        new_value = new_value_magnitude * pnpq_ureg.mpc320_steps
        self.current_state[chan_ident] = new_value

        self.log.info(f"[MPC Stub] Channel {chan_ident} jog {jog_direction}")

    def move_absolute(self, chan_ident: ChanIdent, position: Quantity) -> None:
        # Convert distance to mpc320 steps and check for errors
        absolute_degree = position.to("degree").magnitude
        if absolute_degree < 0 or absolute_degree > 170:
            raise ValueError(
                f"Absolute position must be between 0 and 170 degrees (or equivalent). Value given was {absolute_degree} degrees."
            )

        position_in_steps = position.to("mpc320_steps")
        delta_position = cast(
            Quantity, position_in_steps - self.current_state[chan_ident]
        )
        sleep_delta_position(
            self.time_scaling_factor, self.current_params["velocity"], delta_position
        )

        self.current_state[chan_ident] = cast(Quantity, position_in_steps)

        self.log.info(f"[MPC Stub] Channel {chan_ident} move to {position}")

    def set_channel_enabled(self, chan_ident: ChanIdent, enabled: bool) -> None:
        # No-op for stub device
        pass

    def get_params(self) -> PolarizationControllerParams:
        return self.current_params

    def set_params(
        self,
        velocity: None | Quantity = None,
        home_position: None | Quantity = None,
        jog_step_1: None | Quantity = None,
        jog_step_2: None | Quantity = None,
        jog_step_3: None | Quantity = None,
    ) -> None:
        if velocity is not None:
            self.current_params["velocity"] = cast(
                Quantity, velocity.to("mpc320_velocity")
            )
        if home_position is not None:
            self.current_params["home_position"] = cast(
                Quantity, home_position.to("mpc320_steps")
            )
        if jog_step_1 is not None:
            self.current_params["jog_step_1"] = cast(
                Quantity, jog_step_1.to("mpc320_steps")
            )
        if jog_step_2 is not None:
            self.current_params["jog_step_2"] = cast(
                Quantity, jog_step_2.to("mpc320_steps")
            )
        if jog_step_3 is not None:
            self.current_params["jog_step_3"] = cast(
                Quantity, jog_step_3.to("mpc320_steps")
            )

        self.log.info(f"[MPC Stub] Updated parameters: {self.current_params}")
