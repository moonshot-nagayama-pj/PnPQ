from dataclasses import dataclass, field
from types import TracebackType

from pnpq.devices.switch_thorlabs_osw_e import AbstractOpticalSwitchThorlabsE, State


@dataclass(kw_only=True)
class OpticalSwitchThorlabsEStub(AbstractOpticalSwitchThorlabsE):
    _is_open: bool = field(default=False)
    _current_state: State = field(default=State.BAR)

    def set_state(self, state: State) -> None:
        self._fail_if_not_open()
        self._current_state = state

    def get_state(self) -> State:
        self._fail_if_not_open()
        return self._current_state

    def get_type_code(self) -> str:
        self._fail_if_not_open()
        return "0"

    def get_board_name(self) -> str:
        self._fail_if_not_open()
        return "Stub Optical Switch v1.0"

    def open(self) -> None:
        self._is_open = True

    def close(self) -> None:
        self._fail_if_not_open()
        self._is_open = False

    def __enter__(self) -> "AbstractOpticalSwitchThorlabsE":
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def _fail_if_not_open(self) -> None:
        if not self._is_open:
            raise RuntimeError("Switch connection is not open")
