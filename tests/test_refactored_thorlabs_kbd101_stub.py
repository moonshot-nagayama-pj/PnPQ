from typing import cast

import pytest
from pint import Quantity

from pnpq.apt.protocol import (
    HomeDirection,
    JogDirection,
    JogMode,
    LimitSwitch,
    StopMode,
)
from pnpq.devices.refactored_odl_thorlabs_kbd101 import (
    AbstractOpticalDelayLineThorlabsKBD101,
)
from pnpq.devices.refactored_odl_thorlabs_kbd101_stub import (
    OpticalDelayLineThorlabsKBD101Stub,
)
from pnpq.units import pnpq_ureg


@pytest.fixture(name="stub_odl")
def stub_odl_fixture() -> AbstractOpticalDelayLineThorlabsKBD101:
    odl = OpticalDelayLineThorlabsKBD101Stub()
    return odl


def test_identify(stub_odl: AbstractOpticalDelayLineThorlabsKBD101) -> None:
    stub_odl.identify()


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
