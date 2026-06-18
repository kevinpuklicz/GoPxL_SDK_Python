"""GoDataSet - mirrors GoPxLSdk::GoDataSet."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class GoDataSet:
    _msgs: list = field(default_factory=list)
    _sender: object | None = None

    def clear(self) -> None:
        self._msgs.clear()

    def add(self, msg) -> None:
        self._msgs.append(msg)

    def count(self) -> int:
        return len(self._msgs)

    def gdp_msg_at(self, index: int):
        return self._msgs[index]

    def set_sender(self, sender) -> None:
        self._sender = sender

    def sender(self):
        return self._sender

