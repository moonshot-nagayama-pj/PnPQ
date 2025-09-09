import time
from typing import Generator

import pytest
import structlog

from pnpq.devices.switch_thorlabs_osw_e import (
    AbstractOpticalSwitchThorlabsE,
    OpticalSwitchThorlabsE,
    State,
)

log = structlog.get_logger()


@pytest.fixture(name="device", scope="function")
def device_fixture() -> Generator[AbstractOpticalSwitchThorlabsE]:
    with OpticalSwitchThorlabsE(serial_number="OS7G01RE") as device:
        yield device


def test_set_state(device: AbstractOpticalSwitchThorlabsE) -> None:
    device.set_state(State.BAR)
    assert device.get_state() == State.BAR
    time.sleep(1)
    device.set_state(State.CROSS)
    assert device.get_state() == State.CROSS


def test_get_device_info(device: AbstractOpticalSwitchThorlabsE) -> None:
    type_code = device.get_type_code()
    log.info(f"Type code: {type_code}")
    board_name = device.get_board_name()
    log.info(f"Board name: {board_name}")
