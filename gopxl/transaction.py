"""GoTransaction - mirrors GoPxLSdk::GoTransaction."""

from __future__ import annotations

import threading

from .def_ import DEFAULT_TRANSACTION_TIMEOUT_MSEC
from .enums import GoStatus
from .exceptions import GoChannelError, GoRequestError
from .request import GoRequest
from .response import GoRequestResponse


class GoTransaction:
    __slots__ = ("_request", "_event", "_response", "_error")

    def __init__(self, request: GoRequest):
        self._request = request
        self._event = threading.Event()
        self._response: GoRequestResponse | None = None
        self._error: Exception | None = None

    @property
    def request(self) -> GoRequest:
        return self._request

    def _on_response(self, response: GoRequestResponse) -> None:
        self._response = response
        self._event.set()

    def _on_error(self, error: Exception) -> None:
        self._error = error
        self._event.set()

    def check_response(self, timeout_ms: int = DEFAULT_TRANSACTION_TIMEOUT_MSEC) -> None:
        self.get_response(timeout_ms)

    def get_response(self, timeout_ms: int = DEFAULT_TRANSACTION_TIMEOUT_MSEC) -> GoRequestResponse:
        if not self._event.wait(timeout_ms / 1000.0):
            raise GoChannelError("Request timed out")
        if self._error is not None:
            raise GoChannelError(str(self._error))
        if self._response is None:
            raise GoChannelError("No response received")
        if self._response.status != GoStatus.OK:
            raise GoRequestError(
                f"Request failed for {self._response.path} (status {int(self._response.status)})",
                response=self._response,
            )
        return self._response
