import time

import structlog
from pint import Quantity

log = structlog.get_logger()


def sleep_delta_position(
    time_multiplier: float, velocity: Quantity, delta_position: Quantity
) -> None:
    if time_multiplier < 0.0:
        raise ValueError("Time multiplier must be greater than or equal to 0.0.")
    if time_multiplier == 0.0:
        return

    # Since the velocity can be in different units, we need to convert it to a common unit
    # before calculating the sleep time.
    # However, there are no transformations defined between device-specific velocities,
    # device-specific positions, and standard time units (seconds).
    #
    # Therefore, we first convert the delta position and velocity to a common unit
    # and then calculate the time to sleep.
    #
    # We must split the logic based on the velocity units to ensure correct calculations.
    # as some devices use degrees (mpc320, k10cr1) and others use meters (kbd101).
    if velocity.units in ("mpc320_velocity", "k10cr1_velocity"):
        time_to_move = (
            abs(
                (
                    delta_position.to("degrees") / velocity.to("degrees / second")
                ).magnitude
            )
            * time_multiplier
        )
    elif velocity.units in ("kbd101_velocity",):

        time_to_move = (
            abs(
                (delta_position.to("meters") / velocity.to("meters / second")).magnitude
            )
            * time_multiplier
        )
    else:
        raise AttributeError(
            f"Unsupported velocity units: {velocity.units}. Supported units are 'mpc320_velocity', 'k10cr1_velocity', and 'kbd101_velocity'."
        )

    time.sleep(time_to_move)

    log.info(
        f"[Mock Util] Slept for {time_to_move:.2f} seconds to simulate moving {delta_position} at {velocity}."
    )
