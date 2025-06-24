from typing import Generator

import pytest

from pnpq.apt.connection import AptConnection
from pnpq.devices.odl_thorlabs_kbd101 import OpticalDelayLineThorlabsKBD101
from pnpq.units import pnpq_ureg


@pytest.fixture(name="device", scope="function")
def device_fixture() -> Generator[OpticalDelayLineThorlabsKBD101]:
    with AptConnection(serial_number="28252054") as connection:
        yield OpticalDelayLineThorlabsKBD101(connection=connection)


def test_home(device: OpticalDelayLineThorlabsKBD101) -> None:
    device.home()


def test_move_absolute(device: OpticalDelayLineThorlabsKBD101) -> None:
    device.move_absolute(0 * pnpq_ureg.mm)
    device.move_absolute(15 * pnpq_ureg.mm)


def test_move_outside_limits(device: OpticalDelayLineThorlabsKBD101) -> None:
    with pytest.raises(RuntimeError):
        device.move_absolute(120 * pnpq_ureg.mm)
