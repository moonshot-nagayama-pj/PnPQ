import pytest

from pnpq.apt.protocol import ChanIdent, JogDirection
from pnpq.devices.polarization_controller_thorlabs_mpc import (
    AbstractPolarizationControllerThorlabsMPC,
)
from pnpq.devices.polarization_controller_thorlabs_mpc_stub import (
    PolarizationControllerThorlabsMPC320Stub,
)
from pnpq.units import pnpq_ureg


@pytest.fixture(name="stub_mpc")
def stub_mpc_fixture() -> AbstractPolarizationControllerThorlabsMPC:
    mpc = PolarizationControllerThorlabsMPC320Stub()
    return mpc


@pytest.mark.parametrize(
    "channel", [ChanIdent.CHANNEL_1, ChanIdent.CHANNEL_2, ChanIdent.CHANNEL_3]
)
def test_move_absolute(
    stub_mpc: AbstractPolarizationControllerThorlabsMPC, channel: ChanIdent
) -> None:
    position = 45 * pnpq_ureg.degree

    stub_mpc.move_absolute(channel, position)
    mpc_position = stub_mpc.get_status(channel).position * pnpq_ureg.mpc320_step
    assert mpc_position.to("degree").magnitude == pytest.approx(45, abs=0.05)


@pytest.mark.parametrize(
    "channel", [ChanIdent.CHANNEL_1, ChanIdent.CHANNEL_2, ChanIdent.CHANNEL_3]
)
def test_home(
    stub_mpc: AbstractPolarizationControllerThorlabsMPC, channel: ChanIdent
) -> None:
    position = 45 * pnpq_ureg.degree
    stub_mpc.move_absolute(channel, position)
    stub_mpc.home(channel)
    mpc_position = stub_mpc.get_status(channel).position * pnpq_ureg.mpc320_step
    assert mpc_position.magnitude == 0


@pytest.mark.parametrize(
    "channel", [ChanIdent.CHANNEL_1, ChanIdent.CHANNEL_2, ChanIdent.CHANNEL_3]
)
def test_jog(
    stub_mpc: AbstractPolarizationControllerThorlabsMPC, channel: ChanIdent
) -> None:
    position = 100 * pnpq_ureg.mpc320_step
    stub_mpc.move_absolute(channel, position)
    # Using default jog step of 10 steps
    stub_mpc.jog(channel, JogDirection.FORWARD)
    mpc_position = stub_mpc.get_status(channel).position * pnpq_ureg.mpc320_step
    assert mpc_position.magnitude == 110
    stub_mpc.jog(channel, JogDirection.REVERSE)
    mpc_position = stub_mpc.get_status(channel).position * pnpq_ureg.mpc320_step
    assert mpc_position.magnitude == 100


def test_move_out_of_bound(stub_mpc: AbstractPolarizationControllerThorlabsMPC) -> None:
    position = 200 * pnpq_ureg.degree
    with pytest.raises(ValueError):
        stub_mpc.move_absolute(ChanIdent.CHANNEL_1, position)


def test_custom_home_position(
    stub_mpc: AbstractPolarizationControllerThorlabsMPC,
) -> None:
    position = 45 * pnpq_ureg.degree
    stub_mpc.set_params(home_position=position)
    stub_mpc.home(ChanIdent.CHANNEL_1)
    mpc_position = (
        stub_mpc.get_status(ChanIdent.CHANNEL_1).position * pnpq_ureg.mpc320_step
    )
    assert mpc_position.to("degree").magnitude == pytest.approx(45, abs=0.05)
