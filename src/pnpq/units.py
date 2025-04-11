from typing import Any, Callable, cast

import pint
from pint import Quantity, Unit
from pint.facets.context.objects import Transformation
from pint.facets.plain import PlainQuantity

pnpq_ureg = pint.UnitRegistry()

thorlabs_context = pint.Context("thorlabs_context")


def get_unit_transformation(
    input_to_output: Callable[[float], float],
    input_unit: pint.Unit,
    output_unit: pint.Unit,
    output_range: None | tuple[float, float] = None,
    output_rounded: bool = False,
) -> Transformation:

    def to_quantity(
        ureg: pint.UnitRegistry,  # pylint: disable=unused-argument
        value: PlainQuantity[Quantity],
        **kwargs: Any,  # pylint: disable=unused-argument
    ) -> PlainQuantity[Any]:
        output: float = input_to_output(value.to(input_unit).magnitude)

        converted_quantity = Quantity(
            round(output) if output_rounded else output,
            output_unit,
        )
        if (
            output_range
            and not output_range[0] <= converted_quantity.magnitude <= output_range[1]
        ):
            raise ValueError(
                f"Rounded {output_unit} {converted_quantity.magnitude} is out of range {output_range}."
            )
        return converted_quantity

    return to_quantity


# Custom unit definitions for devices
pnpq_ureg.define("mpc320_step = [dimension_mpc320_step]")
pnpq_ureg.define("k10cr1_step = [dimension_k10cr1_step]")

# According to the protocol, velocity is expressed as a percentage of the maximum speed, ranging from 10% to 100%.
# The maximum velocity is defined as 400 degrees per second, so we store velocity as a dimensionless proportion of this value.
# Thus, the unit for mpc_velocity will be set as dimensionless.
# A transformation function (defined below) will convert other units, like degrees per second, into this proportional form.
pnpq_ureg.define("mpc320_velocity = [dimension_mpc320_velocity]")

mpc320_max_velocity: Quantity = cast(
    Quantity, 400 * (pnpq_ureg.degree / pnpq_ureg.second)
)

# According to the protocol (p.41), it states that we should convert 1 degree/sec to 7329109 steps/sec for K10CR1.
# and 1 degree/sec^2 to 1502 steps/sec^2 for acceleration
pnpq_ureg.define("k10cr1_velocity = [dimension_k10cr1_velocity]")
pnpq_ureg.define("k10cr1_acceleration = [dimension_k10cr1_acceleration]")

thorlabs_context.add_transformation(
    "degree",
    "mpc320_step",
    get_unit_transformation(
        input_to_output=lambda degrees: degrees * 1370 / 170,
        input_unit=pnpq_ureg.degree,
        output_unit=pnpq_ureg.mpc320_step,
        output_range=None,
        output_rounded=True,
    ),
)

thorlabs_context.add_transformation(
    "mpc320_step",
    "degree",
    get_unit_transformation(
        input_to_output=lambda steps: steps * 170 / 1370,
        input_unit=pnpq_ureg.mpc320_step,
        output_unit=pnpq_ureg.degree,
        output_range=None,
        output_rounded=False,
    ),
)

thorlabs_context.add_transformation(
    "degree",
    "k10cr1_step",
    get_unit_transformation(
        input_to_output=lambda degrees: degrees * 136533,
        input_unit=pnpq_ureg.degree,
        output_unit=pnpq_ureg.k10cr1_step,
        output_rounded=True,
    ),
)

thorlabs_context.add_transformation(
    "k10cr1_step",
    "degree",
    get_unit_transformation(
        input_to_output=lambda steps: steps / 136533,
        input_unit=pnpq_ureg.k10cr1_step,
        output_unit=pnpq_ureg.degree,
    ),
)

thorlabs_context.add_transformation(
    "degree / second",
    "mpc320_velocity",
    get_unit_transformation(
        input_to_output=lambda degrees: degrees / 400 * 100,
        input_unit=cast(Unit, pnpq_ureg("degree / second")),
        output_unit=pnpq_ureg.mpc320_velocity,
        output_range=(10, 100),
        output_rounded=True,
    ),
    # to_mpc320_velocity,  # Convert value to percent
)

thorlabs_context.add_transformation(
    "mpc320_velocity",
    "degree / second",
    get_unit_transformation(
        input_to_output=lambda steps: steps / 100 * 400,
        input_unit=cast(Unit, pnpq_ureg("mpc320_velocity")),
        output_unit=cast(Unit, pnpq_ureg("degree / second")),
    ),
)

thorlabs_context.add_transformation(
    "mpc320_velocity",
    "mpc320_step / second",
    get_unit_transformation(
        input_to_output=lambda degrees_per_second: degrees_per_second / 170 * 1370,
        input_unit=cast(Unit, pnpq_ureg("degree / second")),
        output_unit=cast(
            Unit, pnpq_ureg("mpc320_step / second")
        ),  # Already rounded because using degrees / second -> mpc320_velocity conversion
    ),
)

thorlabs_context.add_transformation(
    "mpc320_step / second",
    "mpc320_velocity",
    get_unit_transformation(
        input_to_output=lambda step: (
            (step / 1370) * 170 * pnpq_ureg("degree / second")
        )
        .to("mpc320_velocity")
        .magnitude,
        input_unit=cast(Unit, pnpq_ureg("mpc320_step / second")),
        output_unit=cast(Unit, pnpq_ureg("mpc320_velocity")),
    ),
)

# Add K10CR1 velocity transformations
thorlabs_context.add_transformation(
    "degree / second",
    "k10cr1_velocity",
    get_unit_transformation(
        input_to_output=lambda degrees: degrees * 7329109,
        input_unit=cast(Unit, pnpq_ureg("degree / second")),
        output_unit=cast(Unit, pnpq_ureg("k10cr1_velocity")),
        output_rounded=True,
    ),
)

thorlabs_context.add_transformation(
    "k10cr1_velocity",
    "degree / second",
    get_unit_transformation(
        input_to_output=lambda steps: steps / 7329109,
        input_unit=cast(Unit, pnpq_ureg("k10cr1_velocity")),
        output_unit=cast(Unit, pnpq_ureg("degree / second")),
    ),
)

thorlabs_context.add_transformation(
    "k10cr1_velocity",
    "k10cr1_step / second",
    get_unit_transformation(
        input_to_output=lambda degrees_per_second: (degrees_per_second * 136533)
        / 7329109,
        input_unit=cast(Unit, pnpq_ureg("k10cr1_velocity")),
        output_unit=cast(Unit, pnpq_ureg("k10cr1_step / second")),
    ),
)

thorlabs_context.add_transformation(
    "k10cr1_step / second",
    "k10cr1_velocity",
    get_unit_transformation(
        input_to_output=lambda step_per_second: (step_per_second / 136533) * 7329109,
        input_unit=cast(Unit, pnpq_ureg("k10cr1_step / second")),
        output_unit=cast(Unit, pnpq_ureg("k10cr1_velocity")),
        output_rounded=True,
    ),
)

# Add accleleration transformations
thorlabs_context.add_transformation(
    "degree / second ** 2",
    "k10cr1_acceleration",
    get_unit_transformation(
        input_to_output=lambda degrees: degrees * 1502,
        input_unit=cast(Unit, pnpq_ureg("degree / second ** 2")),
        output_unit=cast(Unit, pnpq_ureg("k10cr1_acceleration")),
        output_rounded=True,
    ),
)

thorlabs_context.add_transformation(
    "k10cr1_acceleration",
    "degree / second ** 2",
    get_unit_transformation(
        input_to_output=lambda steps: steps / 1502,
        input_unit=cast(Unit, pnpq_ureg("k10cr1_acceleration")),
        output_unit=cast(Unit, pnpq_ureg("degree / second ** 2")),
    ),
)

thorlabs_context.add_transformation(
    "k10cr1_step / second ** 2",
    "k10cr1_acceleration",
    get_unit_transformation(
        input_to_output=lambda steps_per_sec_squared: (
            (steps_per_sec_squared / 136533) * 1502
        ),
        input_unit=cast(Unit, pnpq_ureg("k10cr1_step / second ** 2")),
        output_unit=cast(Unit, pnpq_ureg("k10cr1_acceleration")),
        output_rounded=True,
    ),
)

thorlabs_context.add_transformation(
    "k10cr1_acceleration",
    "k10cr1_step / second ** 2",
    get_unit_transformation(
        input_to_output=lambda k10cr1_acceleration: (k10cr1_acceleration / 1502)
        * 136533,
        input_unit=cast(Unit, pnpq_ureg("k10cr1_acceleration")),
        output_unit=cast(Unit, pnpq_ureg("k10cr1_step / second ** 2")),
    ),
)

# Add and enable the context
pnpq_ureg.add_context(thorlabs_context)
pnpq_ureg.enable_contexts("thorlabs_context")
