.. PnPQ documentation master file, created by
   sphinx-quickstart on Mon Nov  4 16:16:18 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

PnPQ
====

.. toctree::
   :hidden:
   :maxdepth: 2

   api/modules

PnPQ is a control library for hardware commonly used in quantum optical experiments (although it is probably useful for classical optical experiments as well!).

Supported devices
-----------------

ThorLabs
^^^^^^^^

- :py:mod:`Waveplates (kbd101) <pnpq.devices.waveplate_thorlabs_kb10crm>`
- :py:mod:`Optical Delay Line (kbd101) <pnpq.devices.odl_thorlabs_kbd101>`
- :py:mod:`Optical Switch (osw1310e) <pnpq.devices.switch_thorlabs_osw1310e>`
- :py:mod:`Motorized Polarization Controller (mpc320) <pnpq.devices.polarization_controller_thorlabs_mpc>`

OzOptics
^^^^^^^^

- :py:mod:`Optical Delay Line (650ml) <pnpq.devices.odl_ozoptics_650ml>`

About the project
-----------------

`GitHub <https://github.com/moonshot-nagayama-pj/PnPQ>`_
