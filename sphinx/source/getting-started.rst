Getting Started with PnPQ
=========================

ThorLabs APT devices
--------------------

Many ThorLabs devices use a protocol called APT to communicate over USB. PnPQ supports the following APT devices:

- :py:mod:`Waveplates <pnpq.devices.waveplate_thorlabs_k10cr1>`
- :py:mod:`Optical Delay Line <pnpq.devices.odl_thorlabs_kbd101>`
- :py:mod:`Motorized Polarization Controller <pnpq.devices.polarization_controller_thorlabs_mpc>`

To operate a ThorLabs device that uses the APT protocol, first instantiate a connection, then pass it to the device's initializer as a parameter.

.. code-block:: python

   with AptConnection(serial_number="1234ABCD") as connection:
       device = WaveplateThorlabsK10CR1(connection=connection)
       device.move_absolute(60 * pnpq_ureg.degree)
       # Do more actions with the device

For most devices, the serial number can be found on the label on the device's housing. However, it can also be found in software using ``lsusb -v`` (for Linux systems).

The documentation for APT protocol can be found in `ThorLabs Official Website`_.

.. _Thorlabs Official Website: https://www.thorlabs.com/Software/Motion%20Control/APT_Communications_Protocol.pdf

ThorLabs OSWxx-yyyyE optical switches
-------------------------------------

The :py:mod:`OSWxx-yyyyE series of optical switches <pnpq.devices.switch_thorlabs_osw_e>` from ThorLabs do not use the APT protocol.

Configuring the serial driver
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The FTDI USB serial I/O driver used by this device is integrated into macOS and Linux. However, the driver may not recognize the device's USB vendor and product ID.

It is not possible to fix this on macOS, and it is recommended to do development using a Linux virtual machine.

On Linux, add the following content to ``/etc/udev/rules.d/50-ftdi-sio.rules``:

.. code-block:: none

   ACTION=="add", ATTRS{idVendor}=="1313", ATTRS{idProduct}=="80e0", RUN+="/sbin/modprobe ftdi_sio" RUN+="/bin/sh -c 'echo 1313 80e0 > /sys/bus/usb-serial/drivers/ftdi_sio/new_id'"

Using the optical switch
^^^^^^^^^^^^^^^^^^^^^^^^

The switch class is a context manager. To use it, initialize it by passing the serial number into the initializer.

.. code-block:: python

   with OpticalSwitchThorlabsE(serial_number="1234ABCD") as device:
       device.set_state(State.CROSS)
       # Do more actions with the switch
