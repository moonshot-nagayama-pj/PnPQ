# PnPQ

Plug and Play with Quantum!

PnPQ is a Python library for controlling optical devices used in quantum network testbeds.

## Features

Provides a blocking API that allows for control of Thorlabs and OzOptics devices including:
- Optical delay lines
- Optical switches
- Motorized polarization controllers
- Motorized rotation mounts

Uses [Pint](https://pint.readthedocs.io/en/stable/) to enable safe, transparent conversion between standard scientific units of measurement and each device's internal representation (e.g., converting motor steps into degrees).

Unlike competing libraries, PnPQ's multithreaded architecture enables constant logging of status updates during usage, even while other commands are being sent.

High unit test coverage and complete type safety.

## Documentation

The documentation can be seen at [https://moonshot-nagayama-pj.github.io/PnPQ/](https://moonshot-nagayama-pj.github.io/PnPQ/).

## How to get started

Below is sample code that moves the paddles of a Thorlabs motorized polarization controller (mpc320) with serial number `123456789` to a position representing 160 degrees.
```py
  with AptConnection(serial_number="123456789") as connection:
    device = PolarizationControllerThorlabsMPC320(connection=connection)
    device.move_absolute(ChanIdent.CHANNEL_1, 160 * pnpq_ureg.degree)
```
The `with` syntax is necessary in order to properly open and close the connection object. More details can be seen in the documentation above.

## Contributing

Please see [`CONTRIBUTING.md`](https://github.com/moonshot-nagayama-pj/public-documents/blob/main/CONTRIBUTING.md).

## Getting help

If you have a specific question about how to use our software that is not answered by the documentation, please feel free to create a GitHub issue.

## Citing

If our software significantly contributed to your research, we ask that you cite it in your publications.

The best way to do so is by using the information [in our `CITATION.cff` file](CITATION.cff). GitHub automatically generates APA and BibTeX-style citations from this file and makes them available from the "Cite this repository" link on the right-hand side.

These automatically-generated citations will include a [Zenodo "concept" DOI](https://zenodo.org/help/versioning), which points to the software as a whole. If you wish to indicate the specific version of our software that you used, you can find version-specific DOIs by first looking up [our concept DOI](https://doi.org/10.5281/zenodo.16886214) and then checking the list of available versions at Zenodo.
