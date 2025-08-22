from dataclasses import dataclass, field
from types import TracebackType

from pnpq.devices.switch_thorlabs_osw_e import AbstractOpticalSwitchThorlabsE, State


@dataclass(frozen=True, kw_only=True)
class OpticalSwitchThorlabsEStub(AbstractOpticalSwitchThorlabsE):
    is_opened: bool = field(default=False)
    current_state: State = field(default=State.BAR)

    def set_state(self, state: State) -> None:
        self._fail_if_not_opened()
        object.__setattr__(self, "current_state", state)

    def get_state(self) -> State:
        self._fail_if_not_opened()
        return self.current_state

    def get_query_type(self) -> str:
        self._fail_if_not_opened()
        return "0"

    def get_board_name(self) -> str:
        self._fail_if_not_opened()
        return "Stub Optical Switch v1.0"

    def open(self) -> None:
        object.__setattr__(self, "is_opened", True)

    def close(self) -> None:
        self._fail_if_not_opened()
        object.__setattr__(self, "is_opened", False)

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

    def _fail_if_not_opened(self) -> None:
        if not self.is_opened:
            raise RuntimeError("Switch connection is not opened")
