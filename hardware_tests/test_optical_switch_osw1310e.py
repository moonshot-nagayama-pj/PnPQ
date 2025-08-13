import time
from typing import Generator

import pytest
import structlog

from pnpq.devices.switch_thorlabs_osw1310e import (
    AbstractOpticalSwitchThorlabs1310E,
    OpticalSwitchThorlabs1310E,
    State,
)

log = structlog.get_logger()


@pytest.fixture(name="device", scope="function")
def device_fixture() -> Generator[AbstractOpticalSwitchThorlabs1310E]:
    with OpticalSwitchThorlabs1310E(serial_number="OS7G01RE") as device:
        yield device


def test_set_state(device: AbstractOpticalSwitchThorlabs1310E) -> None:
    device.set_state(State.BAR)
    assert device.get_status() == State.BAR
    time.sleep(1)
    device.set_state(State.CROSS)
    assert device.get_status() == State.CROSS


def test_get_device_info(device: AbstractOpticalSwitchThorlabs1310E) -> None:
    query_type = device.get_query_type()
    log.info(f"Query type: {query_type}")
    board_name = device.get_board_name()
    log.info(f"Board name: {board_name}")
