.. PnPQ documentation master file

PnPQ
====

PnPQ is a control library for hardware commonly used in quantum optical experiments (although it is probably useful for classical optical experiments as well!).

.. toctree::
  :hidden:
  :maxdepth: 2

  api/pnpq.apt
  api/pnpq.devices
  api/pnpq.errors
  api/pnpq.events
  api/pnpq.units

Getting started
---------------

Please see :doc:`Getting Started with PnPQ </getting-started>`.

Supported devices
-----------------

ThorLabs
^^^^^^^^

- :py:mod:`Waveplates (K10CR1, K10CR2) <pnpq.devices.waveplate_thorlabs_k10cr1>`
- :py:mod:`Optical Delay Line (KBD101) <pnpq.devices.odl_thorlabs_kbd101>`
- :py:mod:`Optical Switch (OSWxx-yyyyE) <pnpq.devices.switch_thorlabs_osw_e>`
- :py:mod:`Motorized Polarization Controller (MPC320, MPC220) <pnpq.devices.polarization_controller_thorlabs_mpc>`

OzOptics
^^^^^^^^

- :py:mod:`Optical Delay Line (650ml) <pnpq.devices.odl_ozoptics_650ml>`

Note: The OzOptics driver is still in the process of being refactored. It may not be fully supported, and its API may change in the near future.

About the project
-----------------

`GitHub <https://github.com/moonshot-nagayama-pj/PnPQ>`_
