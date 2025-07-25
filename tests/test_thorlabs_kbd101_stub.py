from typing import Generator, cast
from unittest import mock

import pytest
from pint import Quantity

from pnpq.apt.protocol import (
    HomeDirection,
    JogDirection,
    JogMode,
    LimitSwitch,
    StopMode,
)
from pnpq.devices.odl_thorlabs_kbd101 import (
    AbstractOpticalDelayLineThorlabsKBD101,
    OpticalDelayLineHomeParams,
    OpticalDelayLineJogParams,
    OpticalDelayLineVelocityParams,
)
from pnpq.devices.odl_thorlabs_kbd101_stub import OpticalDelayLineThorlabsKBD101Stub
from pnpq.units import pnpq_ureg


@pytest.fixture(name="stub_odl")
def stub_odl_fixture() -> AbstractOpticalDelayLineThorlabsKBD101:
    odl = OpticalDelayLineThorlabsKBD101Stub()
    return odl


@pytest.fixture(name="mocked_sleep")
def mocked_sleep_fixture() -> Generator[mock.MagicMock]:
    with mock.patch("time.sleep", mock.MagicMock()) as mocked_sleep:
        yield mocked_sleep


def test_identify(stub_odl: AbstractOpticalDelayLineThorlabsKBD101) -> None:
    stub_odl.identify()


def test_move_absolute_sleep_invalid_time_scaling_factor() -> None:
    """Test that an invalid time multiplier raises an error."""

    with pytest.raises(
        ValueError, match="Time multiplier must be greater than or equal to 0.0."
    ):
        OpticalDelayLineThorlabsKBD101Stub(time_scaling_factor=-1.0)


def test_home(stub_odl: AbstractOpticalDelayLineThorlabsKBD101) -> None:
    stub_odl.home()

    current_status = stub_odl.get_status()
    current_position = cast(
        Quantity, current_status.position * pnpq_ureg.kbd101_position
    )
    assert current_position.magnitude == 0


def test_move_absolute(stub_odl: AbstractOpticalDelayLineThorlabsKBD101) -> None:
    position = 20 * pnpq_ureg.mm

    stub_odl.move_absolute(position)

    current_status = stub_odl.get_status()
    current_position = cast(
        Quantity, current_status.position * pnpq_ureg.kbd101_position
    )
    assert current_position.magnitude == pytest.approx(40000)


@pytest.mark.parametrize(
    "position, expected_sleep_time, time_scaling_factor",
    [
        (1000 * pnpq_ureg.mm, 1.0, 1),
    ],
)
def test_move_absolute_sleep(
    mocked_sleep: mock.MagicMock,
    position: Quantity,
    expected_sleep_time: float,
    time_scaling_factor: float,
) -> None:

    optical_velocity_params = OpticalDelayLineVelocityParams()
    optical_velocity_params["maximum_velocity"] = 1000 * pnpq_ureg("mm / second")
    optical_delay_line = OpticalDelayLineThorlabsKBD101Stub(
        time_scaling_factor=time_scaling_factor,
        current_velocity_params=optical_velocity_params,
    )

    optical_delay_line.move_absolute(position)

    # Assert the sleep behavior
    assert mocked_sleep.call_count == 1
    assert mocked_sleep.call_args[0][0] == pytest.approx(expected_sleep_time)


@pytest.mark.parametrize(
    "jog_step, jog_direction, expected_sleep_time, time_scaling_factor",
    [
        (
            1000 * pnpq_ureg.mm,
            JogDirection.FORWARD,
            1.0,
            1,
        )
    ],
)
def test_jog_sleep(
    mocked_sleep: mock.MagicMock,
    jog_step: Quantity,
    jog_direction: JogDirection,
    expected_sleep_time: float,
    time_scaling_factor: float,
) -> None:

    params = OpticalDelayLineJogParams()
    params["jog_maximum_velocity"] = 1000 * pnpq_ureg("mm / second")
    params["jog_step_size"] = jog_step

    optical_delay_line = OpticalDelayLineThorlabsKBD101Stub(
        time_scaling_factor=time_scaling_factor, current_jog_params=params
    )

    optical_delay_line.set_jogparams(jog_step_size=jog_step)

    optical_delay_line.jog(jog_direction)

    assert mocked_sleep.call_count == 1
    assert mocked_sleep.call_args[0][0] == pytest.approx(expected_sleep_time)


@pytest.mark.parametrize(
    "initial_position, expected_sleep_time, time_scaling_factor",
    [
        (1000 * pnpq_ureg.mm, 1.0, 1),
    ],
)
def test_home_sleep(
    mocked_sleep: mock.MagicMock,
    initial_position: Quantity,
    expected_sleep_time: float,
    time_scaling_factor: float,
) -> None:

    params = OpticalDelayLineHomeParams()
    params["home_velocity"] = 1000 * pnpq_ureg("mm / second")

    optical_delay_line = OpticalDelayLineThorlabsKBD101Stub(
        time_scaling_factor=time_scaling_factor, current_home_params=params
    )

    optical_delay_line.move_absolute(initial_position)
    optical_delay_line.home()

    assert mocked_sleep.call_args[0][0] == pytest.approx(expected_sleep_time)
    assert mocked_sleep.call_count == 2  # One for move_absolute, one for home


def test_velparams(stub_odl: AbstractOpticalDelayLineThorlabsKBD101) -> None:
    stub_odl.set_velparams(
        minimum_velocity=0 * pnpq_ureg.kbd101_velocity,
        acceleration=1374 * pnpq_ureg.kbd101_acceleration,
        maximum_velocity=1342177 * pnpq_ureg.kbd101_velocity,
    )

    velparams = stub_odl.get_velparams()

    assert velparams["minimum_velocity"].to("kbd101_velocity").magnitude == 0
    assert velparams["acceleration"].to("kbd101_acceleration").magnitude == 1374
    assert velparams["maximum_velocity"].to("kbd101_velocity").magnitude == 1342177


def test_jogparams(stub_odl: AbstractOpticalDelayLineThorlabsKBD101) -> None:
    stub_odl.set_jogparams(
        jog_mode=JogMode.SINGLE_STEP,
        jog_step_size=1 * pnpq_ureg.kbd101_position,
        jog_minimum_velocity=2 * pnpq_ureg.kbd101_velocity,
        jog_acceleration=3 * pnpq_ureg.kbd101_acceleration,
        jog_maximum_velocity=4 * pnpq_ureg.kbd101_velocity,
        jog_stop_mode=StopMode.IMMEDIATE,
    )

    jogparams = stub_odl.get_jogparams()
    assert jogparams["jog_mode"] == JogMode.SINGLE_STEP
    assert jogparams["jog_step_size"].to("kbd101_position").magnitude == 1
    assert jogparams["jog_minimum_velocity"].to("kbd101_velocity").magnitude == 2
    assert jogparams["jog_acceleration"].to("kbd101_acceleration").magnitude == 3
    assert jogparams["jog_maximum_velocity"].to("kbd101_velocity").magnitude == 4
    assert jogparams["jog_stop_mode"] == StopMode.IMMEDIATE


def test_jog(stub_odl: AbstractOpticalDelayLineThorlabsKBD101) -> None:
    # Default jog for stub ODL is 10mm
    stub_odl.jog(JogDirection.FORWARD)

    current_status = stub_odl.get_status()
    current_position = cast(
        Quantity, current_status.position * pnpq_ureg.kbd101_position
    )
    # Default jog for stub ODL is 10mm
    assert current_position.to("mm").magnitude == pytest.approx(10)

    # Try setting the jog step size to 20mm
    stub_odl.set_jogparams(
        jog_step_size=20 * pnpq_ureg.mm,
    )
    stub_odl.jog(JogDirection.FORWARD)
    current_status = stub_odl.get_status()
    current_position = cast(
        Quantity, current_status.position * pnpq_ureg.kbd101_position
    )
    assert current_position.to("mm").magnitude == pytest.approx(30)

    # Test jog backward
    stub_odl.jog(JogDirection.REVERSE)
    current_status = stub_odl.get_status()
    current_position = cast(
        Quantity, current_status.position * pnpq_ureg.kbd101_position
    )
    assert current_position.to("mm").magnitude == pytest.approx(10)


def test_homeparams(stub_odl: AbstractOpticalDelayLineThorlabsKBD101) -> None:
    stub_odl.set_homeparams(
        home_direction=HomeDirection.FORWARD_0,
        limit_switch=LimitSwitch.HARDWARE_FORWARD,
        home_velocity=1 * pnpq_ureg.kbd101_velocity,
        offset_distance=2 * pnpq_ureg.kbd101_position,
    )

    homeparams = stub_odl.get_homeparams()
    assert homeparams["home_direction"] == HomeDirection.FORWARD_0
    assert homeparams["limit_switch"] == LimitSwitch.HARDWARE_FORWARD
    assert homeparams["home_velocity"].to("kbd101_velocity").magnitude == 1
    assert homeparams["offset_distance"].to("kbd101_position").magnitude == 2
