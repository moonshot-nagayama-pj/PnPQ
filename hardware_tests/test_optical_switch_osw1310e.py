from typing import Generator

import pytest

from pnpq.devices.switch_thorlabs_osw1310e import OpticalSwitchThorlabs1310E, State


@pytest.fixture(name="device", scope="function")
def device_fixture() -> Generator[OpticalSwitchThorlabs1310E]:
    device = OpticalSwitchThorlabs1310E(serial_number="12345678")
    device.open()
    yield device


def test_bar_state(device: OpticalSwitchThorlabs1310E) -> None:
    device.set_state(State.BAR)
    assert device.get_status() == State.BAR


def test_cross_state(device: OpticalSwitchThorlabs1310E) -> None:
    device.set_state(State.CROSS)
    assert device.get_status() == State.CROSS
