import pytest

from pnpq.apt.protocol import ChanIdent
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


def test_move_absolute(stub_odl: AbstractOpticalDelayLineThorlabsKBD101) -> None:
    position = 20 * pnpq_ureg.mm

    stub_odl.move_absolute(position)

    # Currently throws a mypy error because current_state is not in the AbstractWaveplateThorlabsK10CR1.
    # TODO: Replace with get_params when implemented.
    odl_position = stub_odl.current_state[ChanIdent.CHANNEL_1]  # type: ignore

    assert odl_position.magnitude == pytest.approx(40000)


def test_velparams(stub_odl: AbstractOpticalDelayLineThorlabsKBD101) -> None:
    # TODO: Temp value, should fetch one from real device to see the rough idea
    stub_odl.set_velparams(
        minimum_velocity=1 * pnpq_ureg.kbd101_velocity,
        acceleration=2 * pnpq_ureg.kbd101_acceleration,
        maximum_velocity=3 * pnpq_ureg.kbd101_velocity,
    )

    velparams = stub_odl.get_velparams()

    assert velparams["minimum_velocity"].to("kbd101_velocity").magnitude == 1
    assert velparams["acceleration"].to("kbd101_acceleration").magnitude == 2
    assert velparams["maximum_velocity"].to("kbd101_velocity").magnitude == 3
