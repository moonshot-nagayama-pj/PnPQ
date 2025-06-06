from pnpq.devices.refactored_odl_thorlabs_kbd101 import OpticalDelayLineThorlabsKBD101
from pnpq.apt.protocol import ChanIdent
from pnpq.devices.polarization_controller_thorlabs_mpc_stub import PolarizationControllerThorlabsMPC320Stub
from pnpq.units import pnpq_ureg
from pnpq.apt.connection import AptConnection

channel = AptConnection(serial_number="CKBEe12CJ06")


odl = OpticalDelayLineThorlabsKBD101(connection=channel)

position = 25 * pnpq_ureg.millimeter

print(position)

odl.move_absolute(position=position)
