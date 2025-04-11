from typing import Generator

import pytest

from pnpq.apt.connection import AptConnection
from pnpq.devices.refactored_waveplate_thorlabs_k10cr1 import WaveplateThorlabsK10CR1
from pnpq.units import pnpq_ureg


@pytest.fixture(name="device", scope="function")
def device_fixture() -> Generator[WaveplateThorlabsK10CR1]:
    with AptConnection(serial_number="55409764") as connection:
        yield WaveplateThorlabsK10CR1(connection=connection)

# def test_get_velparams(device: WaveplateThorlabsK10CR1) -> None:
#     velparams = device.get_velparams()


def test_move_absolute(device: WaveplateThorlabsK10CR1) -> None:
    # device.move_absolute(0 * pnpq_ureg.degree)
    # Final :24575940
    device.move_absolute(24575940 * pnpq_ureg.k10cr1_steps)
    # device.move_absolute(180 * pnpq_ureg.degree)

# def test_move_absolute2(device: WaveplateThorlabsK10CR1) -> None:
#     # device.move_absolute(0 * pnpq_ureg.degree)
#     device.move_absolute(180 * pnpq_ureg.degree)
