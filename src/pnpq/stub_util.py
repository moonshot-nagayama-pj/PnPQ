import time

import structlog
from pint import DimensionalityError, Quantity

log = structlog.get_logger()


def sleep_delta_position(
    time_multiplier: float, velocity: Quantity, delta_position: Quantity
) -> None:
    if time_multiplier < 0.0:
        raise ValueError("Time multiplier must be greater than or equal to 0.0.")
    if time_multiplier == 0.0:
        return

    # We use the velocity and delta position to calculate the time to sleep.
    # However, there are no transformations defined between device-specific velocities,
    # device-specific positions, and standard time units (seconds).
    #
    # Therefore, we will first try to convert the velocity and delta position to degrees or meters,
    # and if that fails, we will raise an error.
    try:
        time_to_move = (
            abs(
                (
                    delta_position.to("degrees") / velocity.to("degrees / second")
                ).magnitude
            )
            * time_multiplier
        )
    except DimensionalityError as e:
        try:
            time_to_move = (
                abs(
                    (
                        delta_position.to("meter") / velocity.to("meters / second")
                    ).magnitude
                )
                * time_multiplier
            )
        except DimensionalityError:
            raise AttributeError(
                f"Unsupported velocity units: {velocity.units}. Supported units are 'mpc320_velocity', 'k10cr1_velocity', and 'kbd101_velocity'."
            ) from e

    time.sleep(time_to_move)

    log.info(
        f"[Mock Util] Slept for {time_to_move:.2f} seconds to simulate moving {delta_position} at {velocity}."
    )
