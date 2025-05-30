from pnpq.devices.waveplate_thorlabs_kb10crm import Waveplate

print("Hi")
waveplate = Waveplate(serial_port=None, serial_number="55409764")
waveplate.connect()
waveplate.rotate(20)
