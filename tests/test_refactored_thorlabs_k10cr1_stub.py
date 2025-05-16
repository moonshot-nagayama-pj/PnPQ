import pytest

from pnpq.apt.protocol import ChanIdent, HomeDirection, JogMode, LimitSwitch, StopMode
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


def test_jogparams(stub_waveplate: AbstractWaveplateThorlabsK10CR1) -> None:
    stub_waveplate.set_jogparams(
        jog_mode=JogMode.SINGLE_STEP,
        jog_step_size=1 * pnpq_ureg.k10cr1_step,
        jog_minimum_velocity=2 * pnpq_ureg.k10cr1_velocity,
        jog_acceleration=3 * pnpq_ureg.k10cr1_acceleration,
        jog_maximum_velocity=4 * pnpq_ureg.k10cr1_velocity,
        jog_stop_mode=StopMode.IMMEDIATE,
    )

    jogparams = stub_waveplate.get_jogparams()

    assert jogparams["jog_mode"] == JogMode.SINGLE_STEP
    assert jogparams["jog_step_size"].to("k10cr1_step").magnitude == 1
    assert jogparams["jog_minimum_velocity"].to("k10cr1_velocity").magnitude == 2
    assert jogparams["jog_acceleration"].to("k10cr1_acceleration").magnitude == 3
    assert jogparams["jog_maximum_velocity"].to("k10cr1_velocity").magnitude == 4
    assert jogparams["jog_stop_mode"] == StopMode.IMMEDIATE


def test_homeparams(stub_waveplate: AbstractWaveplateThorlabsK10CR1) -> None:
    stub_waveplate.set_homeparams(
        home_direction=HomeDirection.FORWARD_0,
        limit_switch=LimitSwitch.HARDWARE_FORWARD,
        home_velocity=1 * pnpq_ureg.k10cr1_velocity,
        offset_distance=2 * pnpq_ureg.k10cr1_step,
    )

    homeparams = stub_waveplate.get_homeparams()

    assert homeparams["home_direction"] == HomeDirection.FORWARD_0
    assert homeparams["limit_switch"] == LimitSwitch.HARDWARE_FORWARD
    assert homeparams["home_velocity"].to("k10cr1_velocity").magnitude == 1
    assert homeparams["offset_distance"].to("k10cr1_step").magnitude == 2
