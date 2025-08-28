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

The documentation can be found at [https://moonshot-nagayama-pj.github.io/PnPQ/](https://moonshot-nagayama-pj.github.io/PnPQ/).

## Example

Below is sample code that moves the paddles of a Thorlabs motorized polarization controller (mpc320) with serial number `123456789` to a position representing 160 degrees.
```py
  with AptConnection(serial_number="123456789") as connection:
    device = PolarizationControllerThorlabsMPC320(connection=connection)
    device.move_absolute(ChanIdent.CHANNEL_1, 160 * pnpq_ureg.degree)
```
The `with` syntax is necessary in order to properly open and close the connection object.

More information can be found in the [documentation's getting started guide](https://moonshot-nagayama-pj.github.io/PnPQ/).

## Contributing

Please see [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Getting help

If you have a specific question about how to use our software that is not answered by the documentation, please feel free to create a GitHub issue.

## Citing

If our software significantly contributed to your research, we ask that you cite it in your publications.

The best way to do so is by using the metadata in [our `CITATION.cff` file](CITATION.cff).

GitHub automatically generates APA and BibTeX-style citations from this file and makes them available from the "Cite this repository" link on the right-hand side. However, these citations do not include our DOI, making it difficult to locate our software. Please try to include either:

* The [concept DOI](https://zenodo.org/help/versioning), which points to the software as a whole: `10.5281/zenodo.16886214`.
    - This can also be found in `CITATION.cff`.
* A version-specific DOI, which can be found by first looking up [our concept DOI](https://doi.org/10.5281/zenodo.16886214) and then checking the list of available versions at Zenodo. A new DOI is generated for each release.
