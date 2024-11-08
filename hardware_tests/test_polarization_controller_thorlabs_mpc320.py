import pytest
from pint import DimensionalityError

from pnpq.apt.connection import AptConnection
from pnpq.apt.protocol import ChanIdent, JogDirection
from pnpq.devices.polarization_controller_thorlabs_mpc320 import (
    PolarizationControllerThorlabsMPC320,
)
from pnpq.units import ureg
import time

@pytest.fixture(name="device", scope="module")
def device_fixture() -> PolarizationControllerThorlabsMPC320:
    connection = AptConnection(serial_number="38454784")
    return PolarizationControllerThorlabsMPC320(connection=connection)


# def test_check_status(device: PolarizationControllerThorlabsMPC320) -> None:
#    device.check_status()


def test_move_absolute(device: PolarizationControllerThorlabsMPC320) -> None:
    device.identify(ChanIdent.CHANNEL_1)

    device.home(ChanIdent.CHANNEL_1)
    device.home(ChanIdent.CHANNEL_2)
    device.home(ChanIdent.CHANNEL_3)

    device.move_absolute(ChanIdent.CHANNEL_1, 160 * ureg.degree)
    device.move_absolute(ChanIdent.CHANNEL_2, 160 * ureg.degree)
    device.move_absolute(ChanIdent.CHANNEL_3, 160 * ureg.degree)

    # One of the channels on our test device appears to forget to turn
    # off its motor when it's homed or set to 0 degrees. It just sits
    # there vibrating and whining. It's not really safe to leave the
    # device at degree 0 for this reason. 170 also seems too far (160 seems about the safest)
    device.move_absolute(ChanIdent.CHANNEL_1, 10 * ureg.degree)
    device.move_absolute(ChanIdent.CHANNEL_2, 10 * ureg.degree)
    device.move_absolute(ChanIdent.CHANNEL_3, 10 * ureg.degree)

    # device.set_params(home_position=1000)

    # device.home(ChanIdent.CHANNEL_1)
    # device.home(ChanIdent.CHANNEL_2)
    # device.home(ChanIdent.CHANNEL_3)

    # device.move_absolute(ChanIdent.CHANNEL_1, 10 * ureg.degree)
    # device.move_absolute(ChanIdent.CHANNEL_2, 10 * ureg.degree)
    # device.move_absolute(ChanIdent.CHANNEL_3, 10 * ureg.degree)

    # device.set_params(home_position=0 * ureg.degree)

    # device.home(ChanIdent.CHANNEL_1)
    # device.home(ChanIdent.CHANNEL_2)
    # device.home(ChanIdent.CHANNEL_3)

    # device.move_absolute(ChanIdent.CHANNEL_1, 0 * ureg.degree)
    # device.move_absolute(ChanIdent.CHANNEL_2, 0 * ureg.degree)
    # device.move_absolute(ChanIdent.CHANNEL_3, 0 * ureg.degree)

def test_jog(device: PolarizationControllerThorlabsMPC320) -> None:

    device.set_params(jog_step_1=50, jog_step_2=25, jog_step_3=25)

    device.home(ChanIdent.CHANNEL_1)
    device.home(ChanIdent.CHANNEL_2)
    device.home(ChanIdent.CHANNEL_3)


    for i in range(5):
        device.jog(ChanIdent.CHANNEL_1, JogDirection.JOG_FORWARD)
    device.move_absolute(ChanIdent.CHANNEL_1, 5*50 * ureg.mpc320_step)
        # time.sleep(1)
        # device.jog(ChanIdent.CHANNEL_1, JogDirection.JOG_BACKWARD)

        # device.jog(ChanIdent.CHANNEL_2, JogDirection.JOG_BACKWARD)
        # device.jog(ChanIdent.CHANNEL_2, JogDirection.JOG_BACKWARD)
        # device.jog(ChanIdent.CHANNEL_3, JogDirection.JOG_BACKWARD)
        # device.jog(ChanIdent.CHANNEL_3, JogDirection.JOG_BACKWARD)


    # device.jog(ChanIdent.CHANNEL_2, JogDirection.JOG_FORWARD)
    # device.jog(ChanIdent.CHANNEL_1, JogDirection.JOG_FORWARD)



def test_invalid_angle_inputs(device: PolarizationControllerThorlabsMPC320) -> None:
    device.identify(ChanIdent.CHANNEL_1)

    with pytest.raises(ValueError):
        device.move_absolute(ChanIdent.CHANNEL_1, 171 * ureg.degree)
        device.move_absolute(ChanIdent.CHANNEL_1, -1 * ureg.degree)

    with pytest.raises(DimensionalityError):
        device.move_absolute(ChanIdent.CHANNEL_1, 1 * ureg.meter)
