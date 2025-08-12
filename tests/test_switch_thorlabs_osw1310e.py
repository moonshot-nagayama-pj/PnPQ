import pytest

from pnpq.devices.switch_thorlabs_osw1310e import OpticalSwitchThorlabs1310E


def test_disconnected_initialization() -> None:
    with pytest.raises(ValueError):
        with OpticalSwitchThorlabs1310E(serial_number="00000000") as _:
            pass
