from typing import Any, Callable, cast

import pint
from pint import Quantity, Unit
from pint.facets.context.objects import Transformation
from pint.facets.plain import PlainQuantity

pnpq_ureg = pint.UnitRegistry()

thorlabs_context = pint.Context("thorlabs_context")

# Custom unit definitions for devices
pnpq_ureg.define("mpc320_step = [dimension_mpc320_step]")
pnpq_ureg.define("k10cr1_step = [dimension_k10cr1_step]")


# Transformation function for converting between k10cr1_step and degrees
def degree_to_k10cr1_steps(
    ureg: pint.UnitRegistry, value: PlainQuantity[Quantity], **_: Any
) -> PlainQuantity[Any]:
    return Quantity(round(value.to("degree").magnitude * 136533 / 1), ureg.k10cr1_step)


def k10cr1_steps_to_degree(
    ureg: pint.UnitRegistry, value: PlainQuantity[Quantity], **_: Any
) -> PlainQuantity[Any]:
    return Quantity(value.magnitude * 1 / 136533, ureg.degree)


def thorlabs_quantity_to_angle(
    thorlabs_quantity_to_degrees: Callable[[float], float], output_unit: pint.Unit
) -> Transformation:

    def to_angle(
        ureg: pint.UnitRegistry,  # pylint: disable=unused-argument
        value: PlainQuantity[Quantity],
        **kwargs: Any,  # pylint: disable=unused-argument
    ) -> PlainQuantity[Any]:
        return Quantity(
            thorlabs_quantity_to_degrees(float(value.magnitude)),
            output_unit,
        )

    return to_angle


def angle_to_thorlabs_quantity(
    input_to_output: Callable[[float], float],
    input_unit: pint.Unit,
    output_unit: pint.Unit,
    output_range: None | tuple[float, float],
    output_rounded: bool = True,

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


thorlabs_context.add_transformation(
    "degree",
    "mpc320_step",
    angle_to_thorlabs_quantity(
        input_to_output=lambda degrees: degrees * 1370 / 170,
        input_unit=pnpq_ureg.degree,
        output_unit=pnpq_ureg.mpc320_step,
        output_range=None,
    ),
)

thorlabs_context.add_transformation(
    "mpc320_step",
    "degree",
    thorlabs_quantity_to_angle(
        thorlabs_quantity_to_degrees=lambda steps: steps * 170 / 1370,
        output_unit=pnpq_ureg.degree,
    ),
)

thorlabs_context.add_transformation("degree", "k10cr1_step", degree_to_k10cr1_steps)
thorlabs_context.add_transformation("k10cr1_step", "degree", k10cr1_steps_to_degree)

# According to the protocol, velocity is expressed as a percentage of the maximum speed, ranging from 10% to 100%.
# The maximum velocity is defined as 400 degrees per second, so we store velocity as a dimensionless proportion of this value.
# Thus, the unit for mpc_velocity will be set as dimensionless.
# A transformation function (defined below) will convert other units, like degrees per second, into this proportional form.
pnpq_ureg.define("mpc320_velocity = [dimension_mpc320_velocity]")

# According to the protocol (p.41), it states that we should convert 1 degree/sec to 7329109 steps/sec for K10CR1.
# and 1 degree/sec^2 to 1502 steps/sec^2 for acceleration
pnpq_ureg.define("k10cr1_velocity = [dimension_k10cr1_velocity]")
pnpq_ureg.define("k10cr1_acceleration = [dimension_k10cr1_acceleration]")

mpc320_max_velocity: Quantity = cast(
    Quantity, 400 * (pnpq_ureg.degree / pnpq_ureg.second)
)


def to_mpc320_velocity(
    ureg: pint.UnitRegistry, value: PlainQuantity[Quantity], **_: Any
) -> PlainQuantity[Quantity]:
    """
    Converts a given velocity to an mpc320 velocity percentage.
    Raises a ValueError if the rounded velocity is out of the range [10, 100].
    """
    # Ensure velocity is in the same units as max velocity

    velocity_in_degrees: Quantity = cast(Quantity, value.to(mpc320_max_velocity.units))

    converted_velocity = (velocity_in_degrees / mpc320_max_velocity) * 100
    rounded_velocity: Quantity = (
        round(converted_velocity.magnitude) * ureg.mpc320_velocity
    )

    if rounded_velocity.magnitude < 10 or rounded_velocity.magnitude > 100:
        raise ValueError(
            f"Rounded mpc320_velocity {rounded_velocity.magnitude} is out of range (10 to 100)."
        )

    return rounded_velocity


def mpc320_velocity_to_pint_velocity(
    ureg: pint.UnitRegistry, value: PlainQuantity[Quantity], **_: Any
) -> PlainQuantity[Quantity]:
    """
    Converts an mpc320 velocity percentage to a velocity in degrees per second.
    """
    return Quantity(
        (value.magnitude * mpc320_max_velocity) / 100,
        cast(Unit, ureg("degree / second")),
    )


thorlabs_context.add_transformation(
    "degree / second",
    "mpc320_velocity",
    angle_to_thorlabs_quantity(
        input_to_output=lambda degrees: degrees / 400 * 100,
        input_unit=cast(Unit, pnpq_ureg("degree / second")),
        output_unit=pnpq_ureg.mpc320_velocity,
        output_range=(10, 100),
    ),
    # to_mpc320_velocity,  # Convert value to percent
)

thorlabs_context.add_transformation(
    "mpc320_velocity",
    "degree / second",
    thorlabs_quantity_to_angle(
        thorlabs_quantity_to_degrees=lambda steps: steps / 100 * 400,
        output_unit=cast(Unit, pnpq_ureg("degree / second")),
    ),
)


# Add transformations between mpc320_velocity and mpc320_step
def mpc320_velocity_to_mpc320_step_velocity(
    ureg: pint.UnitRegistry, value: PlainQuantity[Quantity], **_: Any
) -> PlainQuantity[Quantity]:
    """
    Converts an mpc320 velocity percentage to a velocity in degrees per second.
    """
    degrees_per_second = value.to("degree / second").magnitude
    steps_per_second = degrees_per_second / 170 * 1370
    return Quantity(steps_per_second, cast(Unit, ureg("mpc320_step / second")))


def mpc320_step_velocity_to_mpc320_velocity(
    ureg: pint.UnitRegistry, value: PlainQuantity[Quantity], **_: Any
) -> PlainQuantity[Quantity]:
    """
    Converts an mpc320 velocity percentage to a velocity in degrees per second.
    """
    degrees_per_second = value.magnitude / 1370 * 170 * ureg("degree / second")
    new_velocity = degrees_per_second.to("mpc320_velocity")
    return cast(Quantity, new_velocity)


thorlabs_context.add_transformation(
    "mpc320_velocity",
    "mpc320_step / second",
    angle_to_thorlabs_quantity(
        input_to_output=lambda step: ( (step / 170 * 1370) * pnpq_ureg("degree / second") ),
        input_unit=cast(Unit, pnpq_ureg("mpc320_velocity")),
        output_unit=cast(Unit, pnpq_ureg("mpc320_step / second")),
        output_range=None,
        output_rounded=False,
    ),
)

thorlabs_context.add_transformation(
    "mpc320_step / second",
    "mpc320_velocity",
    angle_to_thorlabs_quantity(
        input_to_output=lambda step: (step * pnpq_ureg("mpc320_step / second")).to("degree / second").magnitude * 170 / 1370,
        input_unit=cast(Unit, pnpq_ureg("mpc320_step / second")),
        output_unit=cast(Unit, pnpq_ureg("mpc320_velocity")),
        output_range=None,
        output_rounded=False,
    ),
)

# Add and enable the context
pnpq_ureg.add_context(thorlabs_context)
pnpq_ureg.enable_contexts("thorlabs_context")
