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
    device.move_absolute(24575940 * pnpq_ureg.k10cr1_steps)

def test_set_jog_params(device: WaveplateThorlabsK10CR1) -> None:
    device.set_jog_params(
        minimum_velocity=0 * pnpq_ureg.k10cr1_velocity,
        acceleration=0 * pnpq_ureg.k10cr1_acceleration,
        maximum_velocity=10 * pnpq_ureg.k10cr1_velocity,
    )

    ## Matches get jog_params
    jog_params = device.get_jog_params()

    assert jog_params["minimum_velocity"] == 0 * pnpq_ureg.k10cr1_velocity
    assert jog_params["acceleration"] == 0 * pnpq_ureg.k10cr1_acceleration
    assert jog_params["maximum_velocity"] == 10 * pnpq_ureg.k10cr1_velocity
