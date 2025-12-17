from typing import Optional


class DeviceDisconnectedError(Exception):
    """Exception raised for the device is disconnected"""


class DevicePortNotFoundError(Exception):
    """Rasied when a port not found"""


class WaveplateInvalidStepsError(Exception):
    """Raised when a specified step value is more than the device's maximum steps"""


class WavePlateHomedNotCompleted(Exception):
    """Raised when a Homed response has not been received from WavePlate Rotator device"""


class WavePlateCustomRotateError(Exception):
    """Raised when custom rotation failed"""


class WavePlateMoveNotCompleted(Exception):
    """Raised when Moved Complete response has not been receieved from WavePlate Rotator device"""


class WavePlateGetPosNotCompleted(Exception):
    """Raised when GetPos response has not been received from Waveplate Rotator Device"""


class WaveplateEnableChannelError(Exception):
    """Raised when no response has been received from Enable Channel Command"""


class WaveplateInvalidDegreeError(Exception):
    """Raised when an invalid degree specified. degree must be in a range 0-360"""


class WaveplateInvalidMotorChannelError(Exception):
    """Raised when trying to access an invalid motor channel number. check max_channel"""


class OdlMoveNotCompleted(Exception):
    """Raised when Move complete response has not been received from ODL device"""


class OdlHomeNotCompleted(Exception):
    """Raised when Homed response has not been received from ODL device"""


class OdlMoveOutofRangeError(Exception):
    """Raised when the requesed move is our of range of the odl device"""


class OdlGetPosNotCompleted(Exception):
    """Raised when no response has been received for GetPos command"""


class InvalidStateException(Exception):
    """Thrown when a method is called on an object, but the object is
    not in an appropriate state for that function to be called.

    For example, if an object processes streams of data, and those
    streams have already been closed, it should not be possible to
    re-open them.

    """


class ThorlabsOswError(Exception):
    """Exception raised for errors reported by Thorlabs OSWxx-yyyyE devices.

    The instance provides three attributes: ``code`` (int or None),
    ``description`` (str), and ``raw_reply`` (str).
    """

    def __init__(
        self,
        code: Optional[int],
        description: str,
        raw_reply: str,
    ) -> None:
        self.code: Optional[int] = code
        self.description: str = description
        self.raw_reply: str = raw_reply

        code_str = f"{code:02d}" if isinstance(code, int) else "Unknown"
        message = (
            f"Thorlabs OSW error {code_str}: {description}\nRaw reply: {raw_reply}"
        )
        super().__init__(message)


def parse_thorlabs_osw_error(line: str) -> ThorlabsOswError:
    """Parse a reply line into a :class:`ThorlabsOswError`.

    The device normally uses replies of the form ``Error nn,Descriptive text``.
    This function is defensive and still returns an error object for
    malformed lines.
    """
    raw = line.strip()
    lower = raw.lower()

    # Treat anything that does not start with "error" as an error,
    # mark it as an unexpected format.
    if not lower.startswith("error"):
        return ThorlabsOswError(
            code=None,
            description="Reply does not start with 'Error'.",
            raw_reply=raw,
        )

    # Strip off the "Error" prefix (case-insensitive check above) and
    # any following whitespace.
    rest = raw[len("Error") :].lstrip()
    if not rest:
        return ThorlabsOswError(
            code=None,
            description="No content after 'Error' prefix.",
            raw_reply=raw,
        )

    # Expect something like "nn,Descriptive text" or "nn Descriptive text"
    separator = len(rest)
    for ch in (",", " "):
        idx = rest.find(ch)
        if idx != -1 and idx < separator:
            separator = idx

    code_token = rest[:separator].strip()
    description_part = rest[separator:].lstrip(", ").strip()

    try:
        code = int(code_token)
    except ValueError:
        return ThorlabsOswError(
            code=None,
            description="Could not parse error code as integer.",
            raw_reply=raw,
        )

    description = description_part or "No description provided."
    return ThorlabsOswError(
        code=code,
        description=description,
        raw_reply=raw,
    )
