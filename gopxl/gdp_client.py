"""GoGdpClient - mirrors GoPxLSdk::GoGdpClient (minimal)."""

from __future__ import annotations

import socket
import threading
from typing import Callable

from .def_ import DEFAULT_GDP_SERVER_PORT
from .dataset import GoDataSet
from .exceptions import GoChannelError
from .gdp_msg import GoGdpMsg, parse_gdp_message
from .kserializer import read_gdp_packet


class GoGdpClient:
    def __init__(self) -> None:
        self._sock: socket.socket | None = None
        self._connected = False
        self._async = False
        self._receive_thread: threading.Thread | None = None
        self._callback: Callable[[GoDataSet], None] | None = None
        self._dataset = GoDataSet()
        self._ip_address: str = ""
        self._port: int = 0

    def connect(self, ip_address: str, port: int = DEFAULT_GDP_SERVER_PORT, timeout: float = 5.0) -> None:
        if self._connected:
            self.close()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            sock.connect((ip_address, port))
        except OSError as exc:
            sock.close()
            raise GoChannelError(f"Failed to connect GDP to {ip_address}:{port}: {exc}") from exc
        sock.settimeout(1.0)
        self._sock = sock
        self._connected = True
        self._ip_address = ip_address
        self._port = port

    def close(self) -> None:
        self._connected = False
        if self._sock:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self._sock.close()
            except OSError:
                pass
        self._sock = None
        if self._receive_thread and self._receive_thread.is_alive():
            self._receive_thread.join(timeout=2.0)
        self._receive_thread = None
        self._async = False

    def is_connected(self) -> bool:
        return self._connected and self._sock is not None

    def ip_address(self) -> str:
        return self._ip_address

    def port(self) -> int:
        return self._port

    def dataset(self) -> GoDataSet:
        return self._dataset

    def clear_data(self) -> None:
        self._dataset.clear()

    def receive_data_sync(self, timeout_ms: int = 20000) -> None:
        if not self.is_connected() or not self._sock:
            raise GoChannelError("Not connected")
        self._dataset.clear()
        self._dataset.set_sender(self)
        deadline = timeout_ms / 1000.0
        # socket timeout is 1s; loop until last msg or deadline elapses.
        remaining = deadline
        while self.is_connected():
            if remaining <= 0:
                raise GoChannelError("GDP receive timed out")
            try:
                msg_type, packet = read_gdp_packet(self._sock)
                msg = parse_gdp_message(msg_type, packet)
                self._dataset.add(msg)
                if isinstance(msg, GoGdpMsg) and msg.is_last_msg():
                    return
            except socket.timeout:
                remaining -= 1.0
                continue
            except EOFError as exc:
                self._connected = False
                raise GoChannelError(str(exc)) from exc

    def receive_data_async(self, callback: Callable[[GoDataSet], None]) -> None:
        if not self.is_connected():
            raise GoChannelError("Not connected")
        self._callback = callback
        self._async = True
        self._receive_thread = threading.Thread(target=self._async_loop, daemon=True, name="GoGdpClient-recv")
        self._receive_thread.start()

    def _async_loop(self) -> None:
        while self.is_connected() and self._async:
            try:
                self.receive_data_sync(20000)
                if self._callback:
                    self._callback(self._dataset)
            except GoChannelError:
                break

