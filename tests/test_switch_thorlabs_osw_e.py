import pytest

from pnpq.devices.switch_thorlabs_osw_e import OpticalSwitchThorlabsE


def test_disconnected_initialization() -> None:
    with pytest.raises(ValueError):
        with OpticalSwitchThorlabsE(serial_number="00000000") as _:
            pass
