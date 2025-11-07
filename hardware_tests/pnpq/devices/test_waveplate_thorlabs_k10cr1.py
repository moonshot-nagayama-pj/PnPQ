import time
from typing import Generator

import pytest
import structlog

from pnpq.apt.connection import AptConnection
from pnpq.apt.protocol import (
    HomeDirection,
    JogDirection,
    JogMode,
    LimitSwitch,
    StopMode,
)
from pnpq.devices.waveplate_thorlabs_k10cr1 import WaveplateThorlabsK10CR1
from pnpq.units import pnpq_ureg

log = structlog.get_logger()

SERIAL_NUMBER = "55409764"


def test_connection() -> None:
    with AptConnection(serial_number=SERIAL_NUMBER) as connection:
        assert not connection.is_closed()
        time.sleep(1)

        device = WaveplateThorlabsK10CR1(connection=connection)
        time.sleep(1)

        device.move_absolute(0 * pnpq_ureg.degree)
        time.sleep(1)

    assert connection.is_closed()


def test_homed_on_startup() -> None:
    # Unplug and replug the device before running this test.
    with AptConnection(serial_number=SERIAL_NUMBER) as connection:
        device = WaveplateThorlabsK10CR1(connection=connection)
        assert device.is_homed()


@pytest.fixture(name="device", scope="module")
def device_fixture() -> Generator[WaveplateThorlabsK10CR1]:
    with AptConnection(serial_number=SERIAL_NUMBER) as connection:
        yield WaveplateThorlabsK10CR1(connection=connection)


def test_move_absolute(device: WaveplateThorlabsK10CR1) -> None:
    device.move_absolute(0 * pnpq_ureg.degree)
    device.move_absolute(24575940 * pnpq_ureg.k10cr1_steps)


def test_identify(device: WaveplateThorlabsK10CR1) -> None:
    device.identify()


def test_jogparams(device: WaveplateThorlabsK10CR1) -> None:
    mode = JogMode.SINGLE_STEP
    step_size = 10 * pnpq_ureg.degree
    minimum_velocity = 0 * pnpq_ureg.k10cr1_velocity
    acceleration = 30 * pnpq_ureg.degree / pnpq_ureg.second**2
    maximum_velocity = 10 * pnpq_ureg.degree / pnpq_ureg.second
    stop_mode = StopMode.IMMEDIATE

    device.set_jogparams(
        jog_mode=mode,
        jog_step_size=step_size,
        jog_minimum_velocity=minimum_velocity,
        jog_acceleration=acceleration,
        jog_maximum_velocity=maximum_velocity,
        jog_stop_mode=stop_mode,
    )

    jogparams = device.get_jogparams()
    assert jogparams["jog_mode"] == mode
    assert jogparams["jog_step_size"] == step_size.to("k10cr1_step")
    assert jogparams["jog_minimum_velocity"] == minimum_velocity.to("k10cr1_velocity")
    assert jogparams["jog_acceleration"] == acceleration.to("k10cr1_acceleration")
    assert jogparams["jog_maximum_velocity"] == maximum_velocity.to("k10cr1_velocity")
    assert jogparams["jog_stop_mode"] == stop_mode


def test_velparams(device: WaveplateThorlabsK10CR1) -> None:

    velparams = device.get_velparams()
    logger = structlog.get_logger()
    logger.info("Velocity parameters test", velparams=velparams)


def test_homeparams(device: WaveplateThorlabsK10CR1) -> None:

    device.set_homeparams(
        home_direction=HomeDirection.REVERSE,
        limit_switch=LimitSwitch.HARDWARE_REVERSE,
        home_velocity=73291 * pnpq_ureg.k10cr1_velocity * 500,
        offset_distance=2 * pnpq_ureg.k10cr1_step,
    )

    time.sleep(1)

    homeparams = device.get_homeparams()

    assert homeparams["home_direction"] == HomeDirection.REVERSE
    assert homeparams["limit_switch"] == LimitSwitch.HARDWARE_REVERSE
    assert homeparams["home_velocity"].to("k10cr1_velocity").magnitude == 73291 * 500
    assert homeparams["offset_distance"].to("k10cr1_step").magnitude == 2

    log.info("Home parameters test passed", homeparams=homeparams)


def test_home(device: WaveplateThorlabsK10CR1) -> None:
    log.info("Starting home test")
    device.home()


def test_jog(device: WaveplateThorlabsK10CR1) -> None:
    device.jog(
        jog_direction=JogDirection.FORWARD,
    )
    device.jog(
        jog_direction=JogDirection.FORWARD,
    )
    device.jog(
        jog_direction=JogDirection.FORWARD,
    )
