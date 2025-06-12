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
from pnpq.devices.refactored_waveplate_thorlabs_k10cr1 import WaveplateThorlabsK10CR1
from pnpq.units import pnpq_ureg


def test_connection() -> None:
    with AptConnection(serial_number="55409764") as connection:
        assert not connection.is_closed()
        time.sleep(1)

        device = WaveplateThorlabsK10CR1(connection=connection)
        time.sleep(1)

        device.move_absolute(0 * pnpq_ureg.degree)
        time.sleep(1)

    assert connection.is_closed()


def test_homed_on_startup() -> None:
    # Plug and replug the device before running this test.
    with AptConnection(serial_number="55409764") as connection:
        device = WaveplateThorlabsK10CR1(connection=connection)
        assert device.is_homed()


@pytest.fixture(name="device", scope="function")
def device_fixture() -> Generator[WaveplateThorlabsK10CR1]:
    with AptConnection(serial_number="55409764") as connection:
        yield WaveplateThorlabsK10CR1(connection=connection)


def test_move_absolute(device: WaveplateThorlabsK10CR1) -> None:
    device.move_absolute(0 * pnpq_ureg.degree)
    device.move_absolute(24575940 * pnpq_ureg.k10cr1_steps)


def test_identify(device: WaveplateThorlabsK10CR1) -> None:
    device.identify()


def test_jogparams(device: WaveplateThorlabsK10CR1) -> None:
    device.set_jogparams(
        jog_mode=JogMode.SINGLE_STEP,
        jog_step_size=10 * pnpq_ureg.degree,
        jog_minimum_velocity=0 * pnpq_ureg.k10cr1_velocity,
        jog_acceleration=30 * pnpq_ureg.degree / pnpq_ureg.second**2,
        jog_maximum_velocity=10 * pnpq_ureg.degree / pnpq_ureg.second,
        jog_stop_mode=StopMode.IMMEDIATE,
    )

    jogparams = device.get_jogparams()
    assert jogparams["jog_mode"] == JogMode.SINGLE_STEP
    assert jogparams["jog_step_size"].to("k10cr1_step").magnitude == int(
        (10 * pnpq_ureg.degree).to("k10cr1_step").magnitude
    )
    assert jogparams["jog_minimum_velocity"].to("k10cr1_velocity").magnitude == 0
    assert jogparams["jog_acceleration"].to("k10cr1_acceleration").magnitude == int(
        (30 * pnpq_ureg.degree / pnpq_ureg.second**2)
        .to("k10cr1_acceleration")
        .magnitude
    )
    assert jogparams["jog_maximum_velocity"].to("k10cr1_velocity").magnitude == int(
        (10 * pnpq_ureg.degree / pnpq_ureg.second).to("k10cr1_velocity").magnitude
    )
    assert jogparams["jog_stop_mode"] == StopMode.IMMEDIATE


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
    assert homeparams["home_velocity"].to("k10cr1_velocity").magnitude == 73286848
    assert homeparams["offset_distance"].to("k10cr1_step").magnitude == 2

    logger = structlog.get_logger()
    logger.info("Home parameters test passed", homeparams=homeparams)


def test_home(device: WaveplateThorlabsK10CR1) -> None:
    logger = structlog.get_logger()
    logger.info("Starting home test")
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
