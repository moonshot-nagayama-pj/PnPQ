from typing import Generator

import pytest

from pnpq.apt.connection import AptConnection
from pnpq.apt.protocol import HomeDirection, JogDirection, JogMode, LimitSwitch, StopMode
from pnpq.devices.refactored_waveplate_thorlabs_k10cr1 import WaveplateThorlabsK10CR1
from pnpq.units import pnpq_ureg

import structlog

@pytest.fixture(name="device", scope="function")
def device_fixture() -> Generator[WaveplateThorlabsK10CR1]:
    with AptConnection(serial_number="55409764") as connection:
        yield WaveplateThorlabsK10CR1(connection=connection)


# def test_move_absolute(device: WaveplateThorlabsK10CR1) -> None:
#     device.move_absolute(0 * pnpq_ureg.degree)
#     device.move_absolute(24575940 * pnpq_ureg.k10cr1_steps)

# def test_jogparams(device: WaveplateThorlabsK10CR1) -> None:
#     log = structlog.get_logger()
#     device.set_jogparams(
#         jog_mode=JogMode.SINGLE_STEP,
#         jog_step_size=1 * pnpq_ureg.k10cr1_step,
#         jog_minimum_velocity=0 * pnpq_ureg.k10cr1_velocity,
#         jog_acceleration=3 * pnpq_ureg.k10cr1_acceleration,
#         jog_maximum_velocity=4 * pnpq_ureg.k10cr1_velocity,
#         jog_stop_mode=StopMode.IMMEDIATE,
#     )

#     jogparams = device.get_jogparams()

#     assert jogparams["jog_mode"] == JogMode.SINGLE_STEP
#     assert jogparams["jog_step_size"].to("k10cr1_step").magnitude == 1
#     assert jogparams["jog_minimum_velocity"].to("k10cr1_velocity").magnitude == 0
#     assert jogparams["jog_acceleration"].to("k10cr1_acceleration").magnitude == 3
#     assert jogparams["jog_maximum_velocity"].to("k10cr1_velocity").magnitude == 4
#     assert jogparams["jog_stop_mode"] == StopMode.IMMEDIATE

# def test_jog(device: WaveplateThorlabsK10CR1) -> None:
#     device.set_jogparams(
#         jog_mode=JogMode.SINGLE_STEP,
#         jog_step_size=1 * pnpq_ureg.k10cr1_step,
#         jog_minimum_velocity=0 * pnpq_ureg.k10cr1_velocity,
#         jog_acceleration=30 * pnpq_ureg.degree / pnpq_ureg.second**2,
#         jog_maximum_velocity= 10 * pnpq_ureg.degree / pnpq_ureg.second,
#         jog_stop_mode=StopMode.IMMEDIATE,
#     )

#     log = structlog.get_logger()
#     log.info("Starting jog test!!!")

#     device.jog(
#         jog_direction=JogDirection.FORWARD,
#     )

# def test_homeparams(device: WaveplateThorlabsK10CR1) -> None:
    # log = structlog.get_logger()
    # device.set_homeparams(
    #     home_direction=HomeDirection.FORWARD_0,
    #     limit_switch=LimitSwitch.HARDWARE_FORWARD,
    #     home_velocity=1000000 * pnpq_ureg.k10cr1_velocity,
    #     offset_distance=2 * pnpq_ureg.k10cr1_step,
    # )

    # homeparams = device.get_homeparams()

    # assert homeparams["home_direction"] == HomeDirection.FORWARD_0
    # assert homeparams["limit_switch"] == LimitSwitch.HARDWARE_FORWARD
    # assert homeparams["home_velocity"].to("k10cr1_velocity").magnitude == 1000000
    # assert homeparams["offset_distance"].to("k10cr1_step").magnitude == 2

    # logger = structlog.get_logger()
    # logger.info("Home parameters test passed", homeparams=homeparams)


# def test_home(device: WaveplateThorlabsK10CR1) -> None:
#     logger = structlog.get_logger()
#     logger.info("Starting home test")
#     device.home()

def test_jog(device: WaveplateThorlabsK10CR1) -> None:
    device.jog(
        jog_direction=JogDirection.FORWARD,
    )
