import pytest

from pnpq.apt.protocol import ChanIdent
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


def test_velparams(stub_waveplate: AbstractWaveplateThorlabsK10CR1) -> None:
    stub_waveplate.set_velparams(
        minimum_velocity=1 * pnpq_ureg.k10cr1_velocity,
        acceleration=2 * pnpq_ureg.k10cr1_acceleration,
        maximum_velocity=3 * pnpq_ureg.k10cr1_velocity,
    )

    velparams = stub_waveplate.get_velparams()

    assert velparams["minimum_velocity"].to("k10cr1_velocity").magnitude == 1
    assert velparams["acceleration"].to("k10cr1_acceleration").magnitude == 2
    assert velparams["maximum_velocity"].to("k10cr1_velocity").magnitude == 3
