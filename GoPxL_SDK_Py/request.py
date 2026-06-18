"""GoRequest - mirrors GoPxLSdk::GoRequest."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from .enums import GoRequestMethod

_next_id = itertools.count()


@dataclass(slots=True)
class GoRequest:
    method: GoRequestMethod
    uri: str
    content: dict = field(default_factory=dict)
    args: dict = field(default_factory=dict)
    id: int = field(default_factory=lambda: next(_next_id))

    def to_msgpack_body(self) -> dict:
        return {
            "method": self.method.wire_name(),
            "path": self.uri,
            "payload": self.content,
            "args": self.args,
        }
