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

    # Calculate the time it would take to move the given delta position
    time_to_move = (
        abs(
            delta_position.to("degree").magnitude
            / velocity.to("degree / second").magnitude
        )
        * time_multiplier
    )

    time.sleep(time_to_move)

    log.info(
        f"[Mock Util] Slept for {time_to_move:.2f} seconds to simulate moving {delta_position.to('degree').magnitude:.2f} degrees."
    )
