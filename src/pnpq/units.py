from decimal import Decimal
from fractions import Fraction
from typing import Any, TypeAlias, cast

import pint
from pint import Quantity
from pint.facets.plain import PlainQuantity, PlainUnit
from pint.util import UnitsContainer


# Custom class that provides some custom behaviors
class PnPQCustomQuantity(Quantity):
    """
    Custom Quantity class that rounds the magnitude of the value to the nearest integer when the unit is in the list of rounded_units.
    """

    rounded_units = ["mpc320_step"]

    def to(  # pylint: disable=keyword-arg-before-vararg
        self,
        other: (
            PlainQuantity[Any]
            | str
            | dict[str, float | int | Decimal | Fraction | Any]
            | UnitsContainer
            | PlainUnit
            | None
        ) = None,
        *contexts: Any,
        **ctx_kwargs: Any,
    ) -> PlainQuantity[Any]:
        """
        Override implementation to implement rounding behavior.
        """
        value = super().to(other, *contexts, **ctx_kwargs)
        if value.units in self.rounded_units:
            return cast(
                Quantity, PnPQCustomQuantity(round(value.magnitude), value.units)
            )
        return cast(Quantity, value)


# Custom registry
class PnPQCustomUnitRegistry(
    pint.registry.GenericUnitRegistry[PnPQCustomQuantity, pint.Unit]
):  # pylint: disable=too-many-ancestors
    Quantity: TypeAlias = PnPQCustomQuantity
    Unit: TypeAlias = pint.Unit


pnpq_ureg = PnPQCustomUnitRegistry()

# Custom unit definitions for MPC320
pnpq_ureg.define("mpc320_step = (170 / 1370) degree")

# According to the protocol, velocity is expressed as a percentage of the maximum speed, ranging from 10% to 100%.
# The maximum velocity is defined as 400 degrees per second, so we store velocity as a dimensionless proportion of this value.
# Thus, the unit for mpc_velocity will be set as dimensionless.
# A transformation function (defined below) will convert other units, like degrees per second, into this proportional form.
pnpq_ureg.define("mpc320_velocity = []")

context = pint.Context("mpc320_proportional_velocity")

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
        int(round(converted_velocity).magnitude) * ureg.dimensionless
    )

    if rounded_velocity.magnitude < 10 or rounded_velocity.magnitude > 100:
        raise ValueError(
            f"Rounded mpc320_velocity {rounded_velocity.magnitude} is out of range (10 to 100)."
        )

    return rounded_velocity


context.add_transformation(
    "degree / second",
    "mpc320_velocity",
    to_mpc320_velocity,  # Convert value to percent
)

context.add_transformation(
    "mpc320_velocity",
    "degree / second",
    lambda ureg, value, **kwargs: (value * mpc320_max_velocity)
    / 100,  # Convert value from percent
)

pnpq_ureg.add_context(context)
pnpq_ureg.enable_contexts("mpc320_proportional_velocity")
