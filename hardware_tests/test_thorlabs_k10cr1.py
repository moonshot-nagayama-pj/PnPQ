from typing import Generator

import pytest

from pnpq.apt.connection import AptConnection
from pnpq.devices.refactored_waveplate_thorlabs_k10cr1 import WaveplateThorlabsK10CR1
from pnpq.units import pnpq_ureg


@pytest.fixture(name="device", scope="function")
def device_fixture() -> Generator[WaveplateThorlabsK10CR1]:
    with AptConnection(serial_number="55409764") as connection:
        yield WaveplateThorlabsK10CR1(connection=connection)


def test_move_absolute(device: WaveplateThorlabsK10CR1) -> None:
    device.move_absolute(0 * pnpq_ureg.degree)
