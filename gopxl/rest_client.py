"""GoRestClient - TCP control channel REST client (mirrors GoPxLSdk::GoRestClient)."""

from __future__ import annotations

import socket
import struct
import threading
from collections import deque
from typing import Callable

import msgpack

from .def_ import MSGPACK_MESSAGE_TYPE
from .enums import GoRequestMethod
from .exceptions import GoChannelError
from .request import GoRequest
from .response import GoNotificationResponse, GoResponse, GoStreamResponse
from .transaction import GoTransaction

GoNotificationHandler = Callable[[GoNotificationResponse], None]
GoStreamHandler = Callable[[GoStreamResponse], None]
NotificationCallback = Callable[[GoNotificationResponse], None]


def _frame_request(body: bytes) -> bytes:
    inner = struct.pack("<HI", MSGPACK_MESSAGE_TYPE, len(body)) + body
    return struct.pack("<I", len(inner) + 4) + inner


def _drain_frames(buffer: bytearray, handler: Callable[[dict], None]) -> None:
    while len(buffer) >= 4:
        total = struct.unpack_from("<I", buffer, 0)[0]
        if total < 10 or len(buffer) < total:
            return
        frame = bytes(buffer[:total])
        del buffer[:total]
        msg_type, _status, data_len = struct.unpack_from("<HiI", frame, 4)
        if msg_type != MSGPACK_MESSAGE_TYPE:
            continue
        data = frame[14 : 14 + data_len]
        try:
            message = msgpack.unpackb(data, raw=False)
        except msgpack.UnpackException:
            continue
        if isinstance(message, dict):
            handler(message)


class GoRestClient:
    """Persistent TCP REST client using MessagePack carrier protocol."""

    __slots__ = (
        "_sock",
        "_running",
        "_buffer",
        "_lock",
        "_queue",
        "_read_thread",
        "_sub_handler",
        "_stream_handler",
        "_listener_lock",
        "_next_listener_id",
        "_listeners_by_uri",
        "_listener_id_to_uri",
        "_non_idempotent_request_handler",
        "_disconnect_handler",
        "_read_error_handler",
        "_disconnect_fired",
        "address",
        "port",
    )

    def __init__(self) -> None:
        self._sock: socket.socket | None = None
        self._running = False
        self._buffer = bytearray()
        self._lock = threading.Lock()
        self._queue: deque[GoTransaction] = deque()
        self._read_thread: threading.Thread | None = None
        self._sub_handler: GoNotificationHandler | None = None
        self._stream_handler: GoStreamHandler | None = None
        self._listener_lock = threading.Lock()
        self._next_listener_id = 1
        self._listeners_by_uri: dict[str, list[tuple[int, NotificationCallback]]] = {}
        self._listener_id_to_uri: dict[int, str] = {}
        self._non_idempotent_request_handler: Callable[[], None] | None = None
        self._disconnect_handler: Callable[[], None] | None = None
        self._read_error_handler: Callable[[Exception], None] | None = None
        self._disconnect_fired = False
        self.address = ""
        self.port = 0

    def connect(self, address: str, port: int = 0) -> None:
        from .def_ import DEFAULT_CONTROL_PORT

        if self.is_connected():
            return
        if not port:
            port = DEFAULT_CONTROL_PORT
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        try:
            sock.connect((address, port))
        except OSError as exc:
            sock.close()
            raise GoChannelError(f"Failed to connect to {address}:{port}: {exc}") from exc
        sock.settimeout(0.5)
        self._sock = sock
        self.address = address
        self.port = port
        self._running = True
        self._disconnect_fired = False
        self._read_thread = threading.Thread(target=self._read_loop, daemon=True, name="GoRestClient-read")
        self._read_thread.start()

    def disconnect(self) -> None:
        self._running = False
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
        if self._read_thread and self._read_thread.is_alive():
            self._read_thread.join(timeout=2.0)
        self._read_thread = None
        with self._lock:
            self._queue.clear()

    def is_connected(self) -> bool:
        return self._sock is not None and self._running

    def set_sub_handler(self, callback: GoNotificationHandler | None) -> None:
        self._sub_handler = callback

    def set_stream_handler(self, callback: GoStreamHandler | None) -> None:
        self._stream_handler = callback

    def add_notification_listener(self, uri: str, callback: NotificationCallback) -> int:
        if not uri:
            raise ValueError("uri is required")

        need_sub = False
        with self._listener_lock:
            listener_id = self._next_listener_id
            self._next_listener_id += 1

            listeners = self._listeners_by_uri.get(uri)
            if not listeners:
                self._listeners_by_uri[uri] = [(listener_id, callback)]
                need_sub = True
            else:
                listeners.append((listener_id, callback))

            self._listener_id_to_uri[listener_id] = uri

        if need_sub:
            # Best-effort; if the server rejects or we're disconnected, user will still be able to use Sub().
            try:
                self.sub(uri).check_response()
            except Exception:
                pass
        return listener_id

    def remove_notification_listener(self, listener_id: int) -> None:
        uri = None
        need_unsub = False
        with self._listener_lock:
            uri = self._listener_id_to_uri.pop(listener_id, None)
            if not uri:
                return
            listeners = self._listeners_by_uri.get(uri, [])
            listeners = [(i, cb) for (i, cb) in listeners if i != listener_id]
            if listeners:
                self._listeners_by_uri[uri] = listeners
            else:
                self._listeners_by_uri.pop(uri, None)
                need_unsub = True

        if need_unsub and uri:
            try:
                self.unsub(uri).check_response()
            except Exception:
                pass

    def replace_listener_callback(self, listener_id: int, callback: NotificationCallback) -> None:
        with self._listener_lock:
            uri = self._listener_id_to_uri.get(listener_id)
            if not uri:
                return
            listeners = self._listeners_by_uri.get(uri, [])
            self._listeners_by_uri[uri] = [(i, callback if i == listener_id else cb) for (i, cb) in listeners]

    def clear_all_listeners(self) -> None:
        # C++ semantics: clear without sending UnSub (used during disconnect).
        with self._listener_lock:
            self._listeners_by_uri.clear()
            self._listener_id_to_uri.clear()

    def set_non_idempotent_request_handler(self, handler: Callable[[], None] | None) -> None:
        self._non_idempotent_request_handler = handler

    def set_disconnect_handler(self, callback: Callable[[], None] | None) -> None:
        self._disconnect_handler = callback
        self._disconnect_fired = False

    def set_read_error_handler(self, callback: Callable[[Exception], None] | None) -> None:
        self._read_error_handler = callback

    def read(self, uri: str, content: dict | None = None, args: dict | None = None) -> GoTransaction:
        return self._transaction(GoRequestMethod.READ, uri, content, args)

    def update(self, uri: str, content: dict | None = None, args: dict | None = None) -> GoTransaction:
        return self._transaction(GoRequestMethod.UPDATE, uri, content, args)

    def create(self, uri: str, content: dict | None = None, args: dict | None = None) -> GoTransaction:
        return self._transaction(GoRequestMethod.CREATE, uri, content, args)

    def delete(self, uri: str, content: dict | None = None, args: dict | None = None) -> GoTransaction:
        return self._transaction(GoRequestMethod.DELETE, uri, content, args)

    def call(self, uri: str, content: dict | None = None, args: dict | None = None) -> GoTransaction:
        return self._transaction(GoRequestMethod.CALL, uri, content, args)

    def sub(self, uri: str, content: dict | None = None, args: dict | None = None) -> GoTransaction:
        return self._transaction(GoRequestMethod.SUB, uri, content, args)

    def unsub(self, uri: str, content: dict | None = None, args: dict | None = None) -> GoTransaction:
        return self._transaction(GoRequestMethod.UNSUB, uri, content, args)

    def start_stream(self, uri: str, content: dict | None = None, args: dict | None = None) -> GoTransaction:
        return self._transaction(GoRequestMethod.START_STREAM, uri, content, args)

    def stop_stream(self, uri: str, content: dict | None = None, args: dict | None = None) -> GoTransaction:
        return self._transaction(GoRequestMethod.STOP_STREAM, uri, content, args)

    def _transaction(
        self,
        method: GoRequestMethod,
        uri: str,
        content: dict | None,
        args: dict | None,
    ) -> GoTransaction:
        if not self.is_connected() or not self._sock:
            raise GoChannelError("Not connected")
        request = GoRequest(method, uri, content or {}, args or {})
        tx = GoTransaction(request)
        body = msgpack.packb(request.to_msgpack_body(), use_bin_type=True)
        frame = _frame_request(body)
        with self._lock:
            self._queue.append(tx)
        try:
            self._sock.sendall(frame)
        except OSError as exc:
            with self._lock:
                if self._queue and self._queue[-1] is tx:
                    self._queue.pop()
            raise GoChannelError(f"Send failed: {exc}") from exc

        if method in (GoRequestMethod.UPDATE, GoRequestMethod.CREATE, GoRequestMethod.DELETE, GoRequestMethod.CALL):
            if self._non_idempotent_request_handler:
                try:
                    self._non_idempotent_request_handler()
                except Exception:
                    pass
        return tx

    def _read_loop(self) -> None:
        while self._running and self._sock:
            try:
                chunk = self._sock.recv(65536)
                if not chunk:
                    self._on_disconnect()
                    break
                self._buffer.extend(chunk)
                _drain_frames(self._buffer, self._dispatch)
            except socket.timeout:
                continue
            except OSError as exc:
                self._on_read_error(exc)
                break
        self._running = False

    def _dispatch(self, raw: dict) -> None:
        response = GoResponse.from_wire(raw)
        if isinstance(response, GoNotificationResponse):
            # Listener API (C++ v1.5 parity): exact URI matches.
            with self._listener_lock:
                callbacks = list(self._listeners_by_uri.get(response.path, []))
            for _, cb in callbacks:
                threading.Thread(target=cb, args=(response,), daemon=True).start()

            if self._sub_handler:
                threading.Thread(target=self._sub_handler, args=(response,), daemon=True).start()
            return
        if isinstance(response, GoStreamResponse):
            if self._stream_handler:
                threading.Thread(target=self._stream_handler, args=(response,), daemon=True).start()
            return
        with self._lock:
            if self._queue:
                tx = self._queue.popleft()
                tx._on_response(response)  # noqa: SLF001

    def _on_read_error(self, exc: Exception) -> None:
        if self._read_error_handler:
            try:
                self._read_error_handler(exc)
            except Exception:
                pass
        self._on_disconnect()

    def _on_disconnect(self) -> None:
        if self._disconnect_fired:
            return
        self._disconnect_fired = True
        self.clear_all_listeners()
        if self._disconnect_handler:
            try:
                self._disconnect_handler()
            except Exception:
                pass
