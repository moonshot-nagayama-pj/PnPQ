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
    """Raised when a Thorlabs OSWxx-yyyyE optical switch reports an error
    or sends an invalid/unexpected response.

    Attributes
    ----------
    code : int | None
        The numeric error code from the device (e.g. 1, 3, 11), or None if
        the reply could not be parsed.
        The codes correspond to the Thorlabs manual, e.g.:
          01: A general system error occurred
          02: A math domain error was detected
          03: The given value is out of range
          06: Non-volatile memory error
          10: A communication error occurred
          11: The command is unknown
          12: Wrong number of command parameters
          13: The command parameter is invalid
    raw_reply : str
        The raw reply line from the device.
    """

    def __init__(self, code, description: str, raw_reply: str) -> None:
        self.code = code
        self.description = description
        self.raw_reply = raw_reply

        if isinstance(code, int):
            code_str = f"{code:02d}"
        else:
            code_str = "Unknown Code"

        super().__init__(
            f"Thorlabs OSW error {code_str}: {description}\nRaw reply: {raw_reply}"
        )


def parse_thorlabs_osw_error(line: str) -> "ThorlabsOswError":
        """Parse an error reply line from a Thorlabs OSWxx-yyyyE device.
        The manual says the format is:
            "Error nn,Descriptive text"
        """
        raw = line.strip()
        lower = raw.lower()

        # If not starting with "error", identify as unparseable
        if not lower.startswith("error "):
            return ThorlabsOswError(
                code=None,
                description="Reply does not start with 'Error '",
                raw_reply=raw,
            )
        # Remove the space and the "Error" prefix, imply a safer way to parse
        strip = raw[len("Error ") :].strip()
        if not strip:
            return ThorlabsOswError(
                code=None,
                description="No content after 'Error ' prefix",
                raw_reply=raw,
            )
        # Expect something like "nn,Descriptive text" or "nn Descriptive text"
        seperater = len(strip)
        for ch in (",", " "):
            idx = strip.find(ch)
            if idx != -1 and idx < seperater:
                seperater = idx
        # Seperate code and description
        code_part = strip[:seperater].strip()
        description_part = strip[seperater:].lstrip(", ").strip()

        try:
            code_part = int(code_part)
        except ValueError:
            return ThorlabsOswError(
                code=None,
                description="Could not parse error code as integer",
                raw_reply=raw,
            )

        description = (
            description_part if description_part else "No description provided"
        )
        return ThorlabsOswError(
            code=code_part,
            description=description,
            raw_reply=raw,
        )
