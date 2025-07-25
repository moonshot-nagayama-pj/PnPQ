from typing import Generator
from unittest import mock

import pytest
from pint import Quantity

from pnpq.apt.protocol import ChanIdent, JogDirection
from pnpq.devices.polarization_controller_thorlabs_mpc import (
    AbstractPolarizationControllerThorlabsMPC,
    PolarizationControllerParams,
)
from pnpq.devices.polarization_controller_thorlabs_mpc_stub import (
    PolarizationControllerThorlabsMPC320Stub,
)
from pnpq.units import pnpq_ureg


@pytest.fixture(name="stub_mpc")
def stub_mpc_fixture() -> AbstractPolarizationControllerThorlabsMPC:
    mpc = PolarizationControllerThorlabsMPC320Stub()
    return mpc


@pytest.fixture(name="mocked_sleep")
def mocked_sleep_fixture() -> Generator[mock.MagicMock]:
    with mock.patch("time.sleep", mock.MagicMock()) as mocked_sleep:
        yield mocked_sleep


@pytest.mark.parametrize(
    "channel", [ChanIdent.CHANNEL_1, ChanIdent.CHANNEL_2, ChanIdent.CHANNEL_3]
)
def test_move_absolute(
    stub_mpc: AbstractPolarizationControllerThorlabsMPC, channel: ChanIdent
) -> None:
    position = 45 * pnpq_ureg.degree

    stub_mpc.move_absolute(channel, position)
    mpc_position = stub_mpc.get_status(channel).position * pnpq_ureg.mpc320_step
    assert mpc_position.to("degree").magnitude == pytest.approx(45, abs=0.05)


@pytest.mark.parametrize(
    "position, expected_sleep_time, time_scaling_factor",
    [
        (1370 * pnpq_ureg.mpc320_step, 0.5, 1),  # 1370 steps at 1370*2 steps/second
        (685 * pnpq_ureg.mpc320_step, 0.25, 1),  # 685 steps at 1370*2 steps/second
        (1370 * pnpq_ureg.mpc320_step, 1.0, 2),  # Two times more time
        (685 * pnpq_ureg.mpc320_step, 0.5, 2),
    ],
)
def test_move_absolute_sleep(
    mocked_sleep: mock.MagicMock,
    position: Quantity,
    expected_sleep_time: float,
    time_scaling_factor: float,
) -> None:
    """Test that the stub sleeps for the correct amount of time when moving."""

    params = PolarizationControllerParams()
    params["velocity"] = 2 * 1370 * pnpq_ureg("mpc320_step / second")

    mpc = PolarizationControllerThorlabsMPC320Stub(
        time_scaling_factor=time_scaling_factor, current_params=params
    )

    mpc.move_absolute(ChanIdent.CHANNEL_1, position)

    # Assert the sleep behavior
    assert mocked_sleep.call_count == 1
    assert mocked_sleep.call_args[0][0] == expected_sleep_time


@pytest.mark.parametrize(
    "jog_step, jog_direction, expected_sleep_time, time_scaling_factor",
    [
        (
            1370 * pnpq_ureg.mpc320_step,
            JogDirection.FORWARD,
            0.5,
            1,
        ),  # 1370 steps at 1370*2 steps/second
        (
            685 * pnpq_ureg.mpc320_step,
            JogDirection.REVERSE,
            0.25,
            1,
        ),  # 685 steps at 1370*2 steps/second
        (
            1370 * pnpq_ureg.mpc320_step,
            JogDirection.FORWARD,
            1.0,
            2,
        ),  # Two times more time
        (
            685 * pnpq_ureg.mpc320_step,
            JogDirection.REVERSE,
            0.5,
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
    """Test that the stub sleeps for the correct amount of time when jogging."""

    params = PolarizationControllerParams()
    params["velocity"] = 2 * 1370 * pnpq_ureg("mpc320_step / second")

    mpc = PolarizationControllerThorlabsMPC320Stub(
        time_scaling_factor=time_scaling_factor, current_params=params
    )

    mpc.set_params(jog_step_1=jog_step)

    mpc.jog(ChanIdent.CHANNEL_1, jog_direction)

    # Assert the sleep behavior
    assert mocked_sleep.call_count == 1
    assert mocked_sleep.call_args[0][0] == expected_sleep_time


def test_move_absolute_sleep_invalid_time_scaling_factor() -> None:
    """Test that an invalid time multiplier raises an error."""

    with pytest.raises(
        ValueError, match="Time multiplier must be greater than or equal to 0.0."
    ):
        PolarizationControllerThorlabsMPC320Stub(time_scaling_factor=-1.0)


@pytest.mark.parametrize(
    "initial_position, expected_sleep_time, time_scaling_factor",
    [
        (1370 * pnpq_ureg.mpc320_step, 0.5, 1),  # Move to 1370 steps, then home
        (685 * pnpq_ureg.mpc320_step, 0.25, 1),  # Move to 685 steps, then home
        (1370 * pnpq_ureg.mpc320_step, 1.0, 2),  # Two times more time
        (685 * pnpq_ureg.mpc320_step, 0.5, 2),
    ],
)
def test_home_sleep(
    mocked_sleep: mock.MagicMock,
    initial_position: Quantity,
    expected_sleep_time: float,
    time_scaling_factor: float,
) -> None:
    """Test that the stub sleeps for the correct amount of time when homing."""

    params = PolarizationControllerParams()
    params["velocity"] = 2 * 1370 * pnpq_ureg("mpc320_step / second")

    mpc = PolarizationControllerThorlabsMPC320Stub(
        time_scaling_factor=time_scaling_factor, current_params=params
    )

    # Move to the initial position before homing
    mpc.move_absolute(ChanIdent.CHANNEL_1, initial_position)

    # Home the device
    mpc.home(ChanIdent.CHANNEL_1)

    # Assert the sleep behavior
    assert mocked_sleep.call_count == 2  # One for move_absolute, one for home
    assert (
        mocked_sleep.call_args[0][0] == expected_sleep_time
    )  # Homing time based on velocity


@pytest.mark.parametrize(
    "channel", [ChanIdent.CHANNEL_1, ChanIdent.CHANNEL_2, ChanIdent.CHANNEL_3]
)
def test_home(
    stub_mpc: AbstractPolarizationControllerThorlabsMPC, channel: ChanIdent
) -> None:
    position = 45 * pnpq_ureg.degree
    stub_mpc.move_absolute(channel, position)
    stub_mpc.home(channel)
    mpc_position = stub_mpc.get_status(channel).position * pnpq_ureg.mpc320_step
    assert mpc_position.magnitude == 0


@pytest.mark.parametrize(
    "channel", [ChanIdent.CHANNEL_1, ChanIdent.CHANNEL_2, ChanIdent.CHANNEL_3]
)
def test_jog(
    stub_mpc: AbstractPolarizationControllerThorlabsMPC, channel: ChanIdent
) -> None:
    position = 100 * pnpq_ureg.mpc320_step
    stub_mpc.move_absolute(channel, position)
    # Using default jog step of 10 steps
    stub_mpc.jog(channel, JogDirection.FORWARD)
    mpc_position = stub_mpc.get_status(channel).position * pnpq_ureg.mpc320_step
    assert mpc_position.magnitude == 110
    stub_mpc.jog(channel, JogDirection.REVERSE)
    mpc_position = stub_mpc.get_status(channel).position * pnpq_ureg.mpc320_step
    assert mpc_position.magnitude == 100


def test_move_out_of_bound(stub_mpc: AbstractPolarizationControllerThorlabsMPC) -> None:
    position = 200 * pnpq_ureg.degree
    with pytest.raises(ValueError):
        stub_mpc.move_absolute(ChanIdent.CHANNEL_1, position)


def test_custom_home_position(
    stub_mpc: AbstractPolarizationControllerThorlabsMPC,
) -> None:
    position = 45 * pnpq_ureg.degree
    stub_mpc.set_params(home_position=position)
    stub_mpc.home(ChanIdent.CHANNEL_1)
    mpc_position = (
        stub_mpc.get_status(ChanIdent.CHANNEL_1).position * pnpq_ureg.mpc320_step
    )
    assert mpc_position.to("degree").magnitude == pytest.approx(45, abs=0.05)


def test_params(stub_mpc: AbstractPolarizationControllerThorlabsMPC) -> None:
    stub_mpc.set_params(
        velocity=1 * pnpq_ureg("mpc320_velocity"),
        home_position=2 * pnpq_ureg.mpc320_step,
        jog_step_1=3 * pnpq_ureg.mpc320_step,
        jog_step_2=4 * pnpq_ureg.mpc320_step,
        jog_step_3=5 * pnpq_ureg.mpc320_step,
    )
    params = stub_mpc.get_params()

    assert params["velocity"].to("mpc320_velocity").magnitude == 1
    assert params["home_position"].to("mpc320_step").magnitude == 2
    assert params["jog_step_1"].to("mpc320_step").magnitude == 3
    assert params["jog_step_2"].to("mpc320_step").magnitude == 4
    assert params["jog_step_3"].to("mpc320_step").magnitude == 5
