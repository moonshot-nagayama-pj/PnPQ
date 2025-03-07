import pytest

from pnpq.apt.protocol import ChanIdent, JogDirection
from pnpq.devices.polarization_controller_thorlabs_mpc_stub import (
    PolarizationControllerThorlabsMPC320Stub,
)
from pnpq.units import pnpq_ureg


@pytest.fixture(name="stub_mpc")
def stub_waveplate_fixture() -> PolarizationControllerThorlabsMPC320Stub:
    mpc = PolarizationControllerThorlabsMPC320Stub()
    return mpc


@pytest.mark.parametrize(
    "channel", [ChanIdent.CHANNEL_1, ChanIdent.CHANNEL_2, ChanIdent.CHANNEL_3]
)
def test_move_absolute(
    stub_mpc: PolarizationControllerThorlabsMPC320Stub, channel: ChanIdent
) -> None:
    position = 45 * pnpq_ureg.degree

    stub_mpc.move_absolute(channel, position)
    assert stub_mpc.current_state[channel] == position


@pytest.mark.parametrize(
    "channel", [ChanIdent.CHANNEL_1, ChanIdent.CHANNEL_2, ChanIdent.CHANNEL_3]
)
def test_home(
    stub_mpc: PolarizationControllerThorlabsMPC320Stub, channel: ChanIdent
) -> None:
    position = 45 * pnpq_ureg.degree
    stub_mpc.move_absolute(channel, position)
    stub_mpc.home(channel)
    assert stub_mpc.current_state[channel] == 0 * pnpq_ureg.degree


@pytest.mark.parametrize(
    "channel", [ChanIdent.CHANNEL_1, ChanIdent.CHANNEL_2, ChanIdent.CHANNEL_3]
)
def test_jog(
    stub_mpc: PolarizationControllerThorlabsMPC320Stub, channel: ChanIdent
) -> None:
    position = 45 * pnpq_ureg.degree
    stub_mpc.move_absolute(channel, position)
    stub_mpc.jog(channel, JogDirection.FORWARD)
    assert stub_mpc.current_state[channel].to("degree").magnitude == pytest.approx(
        50, abs=0.05
    )
    stub_mpc.jog(channel, JogDirection.REVERSE)
    assert stub_mpc.current_state[channel].to("degree").magnitude == pytest.approx(
        45, abs=0.05
    )


def test_move_out_of_bound(stub_mpc: PolarizationControllerThorlabsMPC320Stub) -> None:
    position = 200 * pnpq_ureg.degree
    with pytest.raises(ValueError):
        stub_mpc.move_absolute(ChanIdent.CHANNEL_1, position)


def test_custom_home_position(
    stub_mpc: PolarizationControllerThorlabsMPC320Stub,
) -> None:
    position = 45 * pnpq_ureg.degree
    stub_mpc.set_params(home_position=position)
    stub_mpc.home(ChanIdent.CHANNEL_1)
    assert stub_mpc.current_state[ChanIdent.CHANNEL_1] == position
