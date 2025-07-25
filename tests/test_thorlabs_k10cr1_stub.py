from typing import Generator
from unittest import mock

import pytest
from pint import Quantity

from pnpq.apt.protocol import (
    ChanIdent,
    HomeDirection,
    JogDirection,
    JogMode,
    LimitSwitch,
    StopMode,
)
from pnpq.devices.waveplate_thorlabs_k10cr1 import (
    AbstractWaveplateThorlabsK10CR1,
    WaveplateHomeParams,
    WaveplateJogParams,
    WaveplateVelocityParams,
)
from pnpq.devices.waveplate_thorlabs_k10cr1_stub import WaveplateThorlabsK10CR1Stub
from pnpq.units import pnpq_ureg


@pytest.fixture(name="stub_waveplate")
def stub_waveplate_fixture() -> AbstractWaveplateThorlabsK10CR1:
    waveplate = WaveplateThorlabsK10CR1Stub()
    return waveplate


@pytest.fixture(name="mocked_sleep")
def mocked_sleep_fixture() -> Generator[mock.MagicMock]:
    with mock.patch("time.sleep", mock.MagicMock()) as mocked_sleep:
        yield mocked_sleep


def test_move_absolute(stub_waveplate: AbstractWaveplateThorlabsK10CR1) -> None:
    position = 45 * pnpq_ureg.degree

    stub_waveplate.move_absolute(position)

    # Currently throws a mypy error because current_state is not in the AbstractWaveplateThorlabsK10CR1.
    # TODO: Replace with get_params when implemented.
    waveplate_position = stub_waveplate.current_state[ChanIdent.CHANNEL_1]  # type: ignore

    assert waveplate_position.to("degree").magnitude == pytest.approx(45)


@pytest.mark.parametrize(
    "position, expected_sleep_time, time_scaling_factor",
    [
        (136533 * pnpq_ureg.k10cr1_step, 1.0, 1),
        (273066 * pnpq_ureg.k10cr1_step, 2.0, 1),
        (136533 * pnpq_ureg.k10cr1_step, 2.0, 2),  # Two times more time
        (273066 * pnpq_ureg.k10cr1_step, 4.0, 2),
    ],
)
def test_move_absolute_sleep(
    mocked_sleep: mock.MagicMock,
    position: Quantity,
    expected_sleep_time: float,
    time_scaling_factor: float,
) -> None:

    waveplate_velocity_params = WaveplateVelocityParams()
    waveplate_velocity_params["maximum_velocity"] = 136533 * pnpq_ureg(
        "k10cr1_step / second"
    )
    waveplate = WaveplateThorlabsK10CR1Stub(
        time_scaling_factor=time_scaling_factor,
        current_velocity_params=waveplate_velocity_params,
    )

    waveplate.move_absolute(position)

    assert mocked_sleep.call_count == 1
    assert mocked_sleep.call_args[0][0] == expected_sleep_time


def test_move_absolute_sleep_invalid_time_scaling_factor() -> None:
    """Test that an invalid time multiplier raises an error."""

    with pytest.raises(
        ValueError, match="Time multiplier must be greater than or equal to 0.0."
    ):
        WaveplateThorlabsK10CR1Stub(time_scaling_factor=-1.0)


@pytest.mark.parametrize(
    "jog_step, jog_direction, expected_sleep_time, time_scaling_factor",
    [
        (
            136533 * pnpq_ureg.k10cr1_step,
            JogDirection.FORWARD,
            1.0,
            1,
        ),
        (
            136533 * pnpq_ureg.k10cr1_step,
            JogDirection.REVERSE,
            1.0,
            1,
        ),
        (
            136533 * pnpq_ureg.k10cr1_step,
            JogDirection.FORWARD,
            2.0,
            2,
        ),
        (
            136533 * pnpq_ureg.k10cr1_step,
            JogDirection.REVERSE,
            2.0,
            2,
        ),
    ],
)
def test_jog_sleep(
    mocked_sleep: mock.MagicMock,
    jog_step: Quantity,
    jog_direction: JogDirection,
    expected_sleep_time: float,
    time_scaling_factor: float,
) -> None:

    params = WaveplateJogParams()
    params["jog_maximum_velocity"] = 136533 * pnpq_ureg("k10cr1_step / second")
    params["jog_step_size"] = jog_step

    waveplate = WaveplateThorlabsK10CR1Stub(
        time_scaling_factor=time_scaling_factor, current_jog_params=params
    )

    waveplate.set_jogparams(jog_step_size=jog_step)

    waveplate.jog(jog_direction)

    assert mocked_sleep.call_count == 1
    assert mocked_sleep.call_args[0][0] == expected_sleep_time


@pytest.mark.parametrize(
    "initial_position, expected_sleep_time, time_scaling_factor",
    [
        (136533 * pnpq_ureg.k10cr1_step, 1.0, 1),
        (273066 * pnpq_ureg.k10cr1_step, 2.0, 1),
        (136533 * pnpq_ureg.k10cr1_step, 2.0, 2),
        (273066 * pnpq_ureg.k10cr1_step, 4.0, 2),
    ],
)
def test_home_sleep(
    mocked_sleep: mock.MagicMock,
    initial_position: Quantity,
    expected_sleep_time: float,
    time_scaling_factor: float,
) -> None:

    params = WaveplateHomeParams()
    params["home_velocity"] = 136533 * pnpq_ureg("k10cr1_step / second")

    waveplate = WaveplateThorlabsK10CR1Stub(
        time_scaling_factor=time_scaling_factor, current_home_params=params
    )

    waveplate.move_absolute(initial_position)

    waveplate.home()

    assert mocked_sleep.call_count == 2  # One for move_absolute, one for home
    assert mocked_sleep.call_args[0][0] == expected_sleep_time


def test_jog(stub_waveplate: AbstractWaveplateThorlabsK10CR1) -> None:
    position = 100 * pnpq_ureg.k10cr1_step
    stub_waveplate.move_absolute(position)

    stub_waveplate.get_jogparams()["jog_step_size"] = 10 * pnpq_ureg.k10cr1_step

    stub_waveplate.jog(JogDirection.FORWARD)

    # Currently throws a mypy error because current_state is not in the AbstractWaveplateThorlabsK10CR1.
    # TODO: Replace with get_params when implemented.
    waveplate_position = stub_waveplate.current_state[ChanIdent.CHANNEL_1]  # type: ignore

    assert waveplate_position.to("k10cr1_step").magnitude == 110
    stub_waveplate.jog(JogDirection.REVERSE)

    # Look above
    waveplate_position = stub_waveplate.current_state[ChanIdent.CHANNEL_1]  # type: ignore
    assert waveplate_position.magnitude == 100


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
