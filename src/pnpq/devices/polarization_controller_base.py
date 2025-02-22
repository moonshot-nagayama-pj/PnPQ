from abc import ABC, abstractmethod
from typing import TypedDict

import structlog
from pint import Quantity

from ..apt.connection import AptConnection
from ..apt.protocol import (
    AptMessage_MGMSG_MOT_GET_USTATUSUPDATE,
    ChanIdent,
    JogDirection,
)


class PolarizationControllerParams(TypedDict):
    #: Dimensionality must be ([angle] / [time]) or mpc320_velocity
    velocity: Quantity
    #: Dimensionality must be [angle] or mpc320_step
    home_position: Quantity
    #: Dimensionality must be [angle] or mpc320_step
    jog_step_1: Quantity
    #: Dimensionality must be [angle] or mpc320_step
    jog_step_2: Quantity
    #: Dimensionality must be [angle] or mpc320_step
    jog_step_3: Quantity


class PolarizationControllerBase(ABC):
    connection: AptConnection

    log = structlog.get_logger()

    # Setup channels for the device
    available_channels: frozenset[ChanIdent] = frozenset([])

    def get_status_all(self) -> tuple[AptMessage_MGMSG_MOT_GET_USTATUSUPDATE, ...]:
        all_status = []
        for channel in self.available_channels:
            status = self.get_status(channel)
            all_status.append(status)
        return tuple(all_status)

    @abstractmethod
    def get_status(
        self, chan_ident: ChanIdent
    ) -> AptMessage_MGMSG_MOT_GET_USTATUSUPDATE:
        pass

    @abstractmethod
    def home(self, chan_ident: ChanIdent) -> None:
        pass

    @abstractmethod
    def identify(self, chan_ident: ChanIdent) -> None:
        pass

    @abstractmethod
    def jog(self, chan_ident: ChanIdent, jog_direction: JogDirection) -> None:
        """Jogs the device forward or backwards in small steps.
        Experimentally, jog steps of 50 or greater seem to work the
        best.

        The specific number of steps per jog can be set via the
        :py:func:`set_params` function.

        :param chan_ident: The motor channel to jog.
        :param jog_direction: The direction the paddle should move in.

        """

    @abstractmethod
    def move_absolute(self, chan_ident: ChanIdent, position: Quantity) -> None:
        pass

    @abstractmethod
    def get_params(self) -> PolarizationControllerParams:
        pass

    @abstractmethod
    def set_channel_enabled(self, chan_ident: ChanIdent, enabled: bool) -> None:
        pass

    @abstractmethod
    def set_params(
        self,
        velocity: None | Quantity = None,
        home_position: None | Quantity = None,
        jog_step_1: None | Quantity = None,
        jog_step_2: None | Quantity = None,
        jog_step_3: None | Quantity = None,
    ) -> None:
        pass
