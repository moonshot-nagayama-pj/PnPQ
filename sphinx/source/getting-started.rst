.. _getting-started-guide:

Getting Started with PnPQ
=========================

ThorLabs APT devices
--------------------

Many ThorLabs devices use a protocol called APT to communicate via serial. Those supported by PnPQ that uses the APT protocol includes:

- Waveplates
- Optical Delay Line
- Motorized Polarization Controller

To operate a ThorLabs device that uses the APT protocol, first instantiate a connection, then pass it to the device's initializer as a parameter.

.. code-block:: python

   with AptConnection(serial_number="1234ABCD") as connection:
       device = WaveplateThorlabsK10CR1(connection=connection)
       device.move_absolute(60 * pnpq_ureg.degree)
       # Do more actions with the device

For most devices, the serial number can be found on the label on the device's housing. However, it can also be found in software using ``lsusb -v`` (for Linux systems).

The documentation for APT protocol can be found in `ThorLabs Official Website`_.

.. _Thorlabs Official Website: https://www.thorlabs.com/Software/Motion%20Control/APT_Communications_Protocol.pdf
