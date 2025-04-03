import pytest

from pnpq.apt.protocol import ChanIdent, JogDirection
from pnpq.devices.polarization_controller_thorlabs_mpc import (
    AbstractPolarizationControllerThorlabsMPC,
)
from pnpq.devices.polarization_controller_thorlabs_mpc_stub import (
    PolarizationControllerThorlabsMPC320Stub,
)
from pnpq.devices.refactored_waveplate_thorlabs_k10cr1 import (
    AbstractWaveplateThorlabsK10CR1,
)
from pnpq.devices.refactored_waveplate_thorlabs_k10cr1_stub import (
    WaveplateThorlabsK10CR1Stub,
)
from pnpq.units import pnpq_ureg


@pytest.fixture(name="stub_waveplate")
def stub_waveplate_fixture() -> AbstractWaveplateThorlabsK10CR1:
    waveplate = WaveplateThorlabsK10CR1Stub()
    return waveplate


def test_move_absolute(stub_waveplate: AbstractWaveplateThorlabsK10CR1) -> None:
    position = 45 * pnpq_ureg.degree

    stub_waveplate.move_absolute(position)

    # Currently throws a mypy error because current_state is not in the AbstractWaveplateThorlabsK10CR1.
    # TODO: Replace with get_params when implemented.
    waveplate_position = stub_waveplate.current_state[ChanIdent.CHANNEL_1]  # type: ignore

    assert waveplate_position.to("degree").magnitude == pytest.approx(45)
