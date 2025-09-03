from typing import Generator

import pytest

from pnpq.devices.switch_thorlabs_osw_e import AbstractOpticalSwitchThorlabsE, State
from pnpq.devices.switch_thorlabs_osw_e_stub import OpticalSwitchThorlabsEStub


def test_disconnected_switch() -> None:
    switch = OpticalSwitchThorlabsEStub()
    with pytest.raises(RuntimeError):
        switch.get_state()


@pytest.fixture(name="connected_switch")
def connected_switch_fixture() -> Generator[AbstractOpticalSwitchThorlabsE]:
    with OpticalSwitchThorlabsEStub() as switch:
        yield switch


def test_set_state(connected_switch: AbstractOpticalSwitchThorlabsE) -> None:
    connected_switch.set_state(State.CROSS)
    assert connected_switch.get_state() == State.CROSS
    connected_switch.set_state(State.BAR)
    assert connected_switch.get_state() == State.BAR


def test_auxiliary_function(connected_switch: AbstractOpticalSwitchThorlabsE) -> None:
    query_type = connected_switch.get_type_code()
    assert query_type == "0"
    board_name = connected_switch.get_board_name()
    assert board_name == "Stub Optical Switch v1.0"
