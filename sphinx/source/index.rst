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

Please see the :ref:`getting started guide <getting-started-guide>`.

Supported devices
-----------------

ThorLabs
^^^^^^^^

- :py:mod:`Waveplates (K10CR1) <pnpq.devices.waveplate_thorlabs_k10cr1>`
- :py:mod:`Optical Delay Line (KBD101) <pnpq.devices.odl_thorlabs_kbd101>`
- :py:mod:`Optical Switch (OSWxx-yyyyE) <pnpq.devices.switch_thorlabs_osw_e>`
- :py:mod:`Motorized Polarization Controller (MPC320) <pnpq.devices.polarization_controller_thorlabs_mpc>`

OzOptics
^^^^^^^^

- :py:mod:`Optical Delay Line (650ml) <pnpq.devices.odl_ozoptics_650ml>`

About the project
-----------------

`GitHub <https://github.com/moonshot-nagayama-pj/PnPQ>`_
