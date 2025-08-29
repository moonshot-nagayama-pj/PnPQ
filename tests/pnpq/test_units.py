import pytest
from pint import Quantity

from pnpq.units import pnpq_ureg


@pytest.mark.parametrize(
    "test_mpc320_step, expected_angle, output_units",
    [
        (-1370, -170, "degree"),
        (0, 0, "degree"),
        (1370, 170, "degree"),
        (1370, 2.96706, "radians"),
    ],
)
def test_mpc320_step_to_angle_conversion(
    test_mpc320_step: float, expected_angle: float, output_units: str
) -> None:

    angle = (test_mpc320_step * pnpq_ureg.mpc320_step).to(output_units).magnitude
    assert angle == pytest.approx(expected_angle)


@pytest.mark.parametrize(
    "test_angle, expected_mpc320_step",
    [
        (-170 * pnpq_ureg.degree, -1370),
        (0 * pnpq_ureg.degree, 0),
        (170 * pnpq_ureg.degree, 1370),
        (169 * pnpq_ureg.degree, 1362),  # This will be able to test the actual rounding
        (90 * pnpq_ureg.degree, 725),
        (1.570796 * pnpq_ureg.radian, 725),
        (100 * pnpq_ureg.mpc320_step, 100),
    ],
)
def test_angle_to_mpc320_step_conversion(
    test_angle: Quantity, expected_mpc320_step: int
) -> None:

    mpc320_step = test_angle.to("mpc320_step").magnitude
    assert mpc320_step == expected_mpc320_step
    assert isinstance(mpc320_step, int)


@pytest.mark.parametrize(
    "test_k10cr1_step, expected_angle, output_units",
    [
        (-136533, -1, "degree"),
        (0, 0, "degree"),
        (136533, 1, "degree"),
        (136533, 0.0174533, "radians"),
    ],
)
def test_k10cr1_step_to_angle_conversion(
    test_k10cr1_step: Quantity, expected_angle: float, output_units: str
) -> None:

    angle = (test_k10cr1_step * pnpq_ureg.k10cr1_step).to(output_units).magnitude
    assert angle == pytest.approx(expected_angle)


@pytest.mark.parametrize(
    "test_angle, expected_k10cr1_step",
    [
        (-1 * pnpq_ureg.degree, -136533),
        (0 * pnpq_ureg.degree, 0),
        (1 * pnpq_ureg.degree, 136533),
        (
            1.000001 * pnpq_ureg.degree,
            136533,
        ),  # This will be able to test the actual rounding
        (0.0174533 * pnpq_ureg.radian, 136533),
        (100 * pnpq_ureg.k10cr1_step, 100),
    ],
)
def test_angle_to_k10cr1_step_conversion(
    test_angle: Quantity, expected_k10cr1_step: int
) -> None:

    k10cr1_step = (test_angle).to("k10cr1_step").magnitude
    assert k10cr1_step == expected_k10cr1_step
    assert isinstance(k10cr1_step, int)


# Test that [angle] / second quantities accurately convert into mpc320_velocity quantities
@pytest.mark.parametrize(
    "angular_velocity, mpc320_velocity",
    [
        (200 * pnpq_ureg("degree / second"), 50),
        (300 * pnpq_ureg("degree / second"), 75),
        (201 * pnpq_ureg("degree / second"), 50),
        (299 * pnpq_ureg("degree / second"), 75),
        (3.49065850399 * pnpq_ureg("radian / second"), 50),
        (5.23598775598 * pnpq_ureg("radian / second"), 75),
        (3.50811179651 * pnpq_ureg("radian / second"), 50),
        (5.21853446346 * pnpq_ureg("radian / second"), 75),
        (1611.76470588 * pnpq_ureg("mpc320_step / second"), 50),
        (2417.64705882 * pnpq_ureg("mpc320_step / second"), 75),
    ],
)
def test_to_mpc320_velocity_conversion(
    angular_velocity: Quantity, mpc320_velocity: float
) -> None:

    proportion = angular_velocity.to("mpc320_velocity")
    assert mpc320_velocity == proportion.magnitude
    assert isinstance(proportion.magnitude, int)


# Test that mpc320_velocity quantities accurately convert back into [angle] / second quantities
@pytest.mark.parametrize(
    "mpc320_velocity, angular_velocity",
    [
        (50, 200 * pnpq_ureg("degree / second")),
        (75, 300 * pnpq_ureg("degree / second")),
        (50, 3.49065850399 * pnpq_ureg("radian / second")),
        (75, 5.23598775598 * pnpq_ureg("radian / second")),
        (50, 1611.76470588 * pnpq_ureg("mpc320_step / second")),
        (75, 2417.64705882 * pnpq_ureg("mpc320_step / second")),
    ],
)
def test_from_mpc320_velocity_conversion(
    mpc320_velocity: float, angular_velocity: Quantity
) -> None:

    proportion = mpc320_velocity * pnpq_ureg.mpc320_velocity
    velocity = proportion.to(angular_velocity.units)
    assert angular_velocity.magnitude == pytest.approx(velocity.magnitude)
    assert angular_velocity.units == velocity.units


@pytest.mark.parametrize(
    "velocity",
    [
        5 * (pnpq_ureg.degree / pnpq_ureg.second),  # Too low
        450 * (pnpq_ureg.degree / pnpq_ureg.second),  # Too high
    ],
)
def test_to_mpc320_velocity_out_of_bounds(velocity: Quantity) -> None:
    with pytest.raises(
        ValueError,
        match="Rounded mpc320_velocity [0-9]+ is out of range \\(10, 100\\)\\.",
    ):
        velocity.to(pnpq_ureg.mpc320_velocity)


# Test that [angle] / second quantities accurately convert into k10cr1_velocity quantities
# According to the protocol documentation (p.41), it states that we should convert 1 degree/sec to 7329109 steps/sec for K10CR1.
@pytest.mark.parametrize(
    "angular_velocity, k10cr1_velocity",
    [
        (1 * pnpq_ureg("degree / second"), 7329109),
        (2 * pnpq_ureg("degree / second"), 14658218),
        (1.00000001 * pnpq_ureg("degree / second"), 7329109),
        (1.99999999 * pnpq_ureg("degree / second"), 14658218),
        (0.01745329251 * pnpq_ureg("radian / second"), 7329109),
        (0.03490658503 * pnpq_ureg("radian / second"), 14658218),
        (136533 * pnpq_ureg("k10cr1_step / second"), 7329109),
        (273066 * pnpq_ureg("k10cr1_step / second"), 14658218),
    ],
)
def test_to_k10cr1_velocity_conversion(
    angular_velocity: Quantity, k10cr1_velocity: float
) -> None:

    pint_k10cr1_velocity = angular_velocity.to("k10cr1_velocity")
    assert k10cr1_velocity == pint_k10cr1_velocity.magnitude
    assert isinstance(pint_k10cr1_velocity.magnitude, int)


@pytest.mark.parametrize(
    "k10cr1_velocity, angular_velocity",
    [
        (7329109, 1 * pnpq_ureg("degree / second")),
        (14658218, 2 * pnpq_ureg("degree / second")),
        (7329109, 0.01745329251 * pnpq_ureg("radian / second")),
        (14658218, 0.03490658503 * pnpq_ureg("radian / second")),
        (7329109, 136533 * pnpq_ureg("k10cr1_step / second")),
        (14658218, 273066 * pnpq_ureg("k10cr1_step / second")),
    ],
)
def test_from_k10cr1_velocity_conversion(
    k10cr1_velocity: float, angular_velocity: Quantity
) -> None:

    pint_k10cr1_velocity = k10cr1_velocity * pnpq_ureg.k10cr1_velocity
    velocity = pint_k10cr1_velocity.to(angular_velocity.units)
    assert angular_velocity.magnitude == pytest.approx(velocity.magnitude)
    assert angular_velocity.units == velocity.units

    # Check if rounded correctly if output units are k10cr1_step per second
    if angular_velocity.units == pnpq_ureg("k10cr1_step / second"):
        assert isinstance(velocity.magnitude, int)


# Test that k10cr1_acceleration quantities accurately convert into [angle] / second^2 quantities
# According to the protocol (p.41), it states that we should convert 1 degree/sec^2 to 1502 steps/sec^2 for acceleration
@pytest.mark.parametrize(
    "angular_acceleration, k10cr1_acceleration",
    [
        (1 * pnpq_ureg("degree / second ** 2"), 1502),
        (2 * pnpq_ureg("degree / second ** 2"), 3004),
        (1.0001 * pnpq_ureg("degree / second ** 2"), 1502),
        (1.9999 * pnpq_ureg("degree / second ** 2"), 3004),
        (0.01745329251 * pnpq_ureg("radian / second ** 2"), 1502),
        (0.03490658503 * pnpq_ureg("radian / second ** 2"), 3004),
        (136533 * pnpq_ureg("k10cr1_step / second ** 2"), 1502),
        (273066 * pnpq_ureg("k10cr1_step / second ** 2"), 3004),
    ],
)
def test_to_k10cr1_acceleration_conversion(
    angular_acceleration: Quantity, k10cr1_acceleration: float
) -> None:

    pint_k10cr1_acceleration = angular_acceleration.to("k10cr1_acceleration")
    assert k10cr1_acceleration == pint_k10cr1_acceleration.magnitude
    assert isinstance(pint_k10cr1_acceleration.magnitude, int)


@pytest.mark.parametrize(
    "k10cr1_acceleration, angular_acceleration",
    [
        (1502, 1 * pnpq_ureg("degree / second ** 2")),
        (3004, 2 * pnpq_ureg("degree / second ** 2")),
        (1502, 0.01745329251 * pnpq_ureg("radian / second ** 2")),
        (3004, 0.03490658503 * pnpq_ureg("radian / second ** 2")),
        (1502, 136533 * pnpq_ureg("k10cr1_step / second ** 2")),
        (3004, 273066 * pnpq_ureg("k10cr1_step / second ** 2")),
    ],
)
def test_from_k10cr1_acceleration_conversion(
    k10cr1_acceleration: float, angular_acceleration: Quantity
) -> None:

    pint_k10cr1_acceleration = k10cr1_acceleration * pnpq_ureg.k10cr1_acceleration
    acceleration = pint_k10cr1_acceleration.to(angular_acceleration.units)
    assert angular_acceleration.magnitude == pytest.approx(acceleration.magnitude)
    assert angular_acceleration.units == acceleration.units

    # Check if rounded correctly if output units are k10cr1_step per second
    if angular_acceleration.units == pnpq_ureg("k10cr1_step / second ** 2"):
        assert isinstance(acceleration.magnitude, int)


@pytest.mark.parametrize(
    "test_kbd101_position, expected_position, output_units",
    [
        (0, 0, "mm"),
        (200000, 100, "mm"),
        (200000, 10, "cm"),
    ],
)
def test_kbd101_position_to_mm_conversion(
    test_kbd101_position: Quantity, expected_position: float, output_units: str
) -> None:

    angle = (
        (test_kbd101_position * pnpq_ureg.kbd101_position).to(output_units).magnitude
    )
    assert angle == pytest.approx(expected_position)


@pytest.mark.parametrize(
    "test_position, expected_kbd101_position",
    [
        (0 * pnpq_ureg.mm, 0),
        (100 * pnpq_ureg.mm, 200000),
        (10 * pnpq_ureg.cm, 200000),
    ],
)
def test_mm_to_kbd101_position_conversion(
    test_position: Quantity, expected_kbd101_position: int
) -> None:

    kbd101_position = test_position.to("kbd101_position").magnitude
    assert kbd101_position == expected_kbd101_position
    assert isinstance(kbd101_position, int)


@pytest.mark.parametrize(
    "test_velocity, expected_kbd101_velocity",
    [
        (1 * pnpq_ureg("mm / second"), 13422),
        (2 * pnpq_ureg("mm / second"), 26844),
        (1 * pnpq_ureg("cm / second"), 134218),
    ],
)
def test_velocity_to_kbd101_velocity(
    test_velocity: Quantity,
    expected_kbd101_velocity: int,
) -> None:
    kbd101_velocity = test_velocity.to("kbd101_velocity").magnitude
    assert kbd101_velocity == expected_kbd101_velocity
    assert isinstance(kbd101_velocity, int)


@pytest.mark.parametrize(
    "kbd101_velocity, expected_velocity",
    [
        (13422, 1 * pnpq_ureg("mm / second")),
        (26844, 2 * pnpq_ureg("mm / second")),
        (134218, 1 * pnpq_ureg("cm / second")),
    ],
)
def test_kbd101_velocity_to_velocity(
    kbd101_velocity: int,
    expected_velocity: Quantity,
) -> None:
    velocity = (kbd101_velocity * pnpq_ureg.kbd101_velocity).to(expected_velocity.units)
    # For some reason this conversion is not that accurate... (hence rel=1e-4 instead of default 1e-6)
    assert velocity.magnitude == pytest.approx(expected_velocity.magnitude, rel=1e-4)
    assert velocity.units == expected_velocity.units


@pytest.mark.parametrize(
    "test_kbd101_acceleration, expected_kbd101_acceleration",
    [
        (1 * pnpq_ureg("mm / second ** 2"), 1),
        (2 * pnpq_ureg("mm / second ** 2"), 3),
        (1 * pnpq_ureg("cm / second ** 2"), 14),
    ],
)
def test_acceleration_to_kbd101_acceleration(
    test_kbd101_acceleration: Quantity,
    expected_kbd101_acceleration: int,
) -> None:
    kbd101_acceleration = test_kbd101_acceleration.to("kbd101_acceleration").magnitude
    assert kbd101_acceleration == expected_kbd101_acceleration
    assert isinstance(kbd101_acceleration, int)


@pytest.mark.parametrize(
    "kbd101_acceleration, expected_acceleration",
    [
        (1, 1 * pnpq_ureg("mm / second ** 2")),
        (3, 2 * pnpq_ureg("mm / second ** 2")),
        (14, 1 * pnpq_ureg("cm / second ** 2")),
    ],
)
def test_kbd101_acceleration_to_acceleration(
    kbd101_acceleration: int,
    expected_acceleration: Quantity,
) -> None:
    acceleration = (kbd101_acceleration * pnpq_ureg.kbd101_acceleration).to(
        expected_acceleration.units
    )
    assert acceleration.magnitude == pytest.approx(expected_acceleration.magnitude)
    assert acceleration.units == expected_acceleration.units
