"""kApi-style binary reader for GDP messages."""

from __future__ import annotations

import math
import socket
import struct
from io import BytesIO


class KSerializerReader:
    __slots__ = ("_stream",)

    def __init__(self, data: bytes | bytearray) -> None:
        self._stream = BytesIO(data)

    def read_exact(self, n: int) -> bytes:
        data = self._stream.read(n)
        if len(data) != n:
            raise EOFError("Unexpected end of GDP data")
        return data

    def read_u8(self) -> int:
        return self.read_exact(1)[0]

    def read_u16(self) -> int:
        return struct.unpack("<H", self.read_exact(2))[0]

    def read_u32(self) -> int:
        return struct.unpack("<I", self.read_exact(4))[0]

    def read_i32(self) -> int:
        return struct.unpack("<i", self.read_exact(4))[0]

    def read_u64(self) -> int:
        return struct.unpack("<Q", self.read_exact(8))[0]

    def read_i64(self) -> int:
        return struct.unpack("<q", self.read_exact(8))[0]

    def read_f32(self) -> float:
        return struct.unpack("<f", self.read_exact(4))[0]

    def read_f64(self) -> float:
        return struct.unpack("<d", self.read_exact(8))[0]

    def read_i16_array(self, count: int) -> list[int]:
        if count <= 0:
            return []
        return list(struct.unpack(f"<{count}h", self.read_exact(count * 2)))

    def read_u8_array(self, count: int) -> bytes:
        if count <= 0:
            return b""
        return self.read_exact(count)

    def read_text(self, length: int) -> str:
        if length <= 0:
            return ""
        return self.read_exact(length).decode("utf-8", errors="replace")

    def section_u32(self) -> KSerializerReader:
        total = self.read_u32()
        return KSerializerReader(self.read_exact(total - 4))

    def section_u16(self) -> KSerializerReader:
        total = self.read_u16()
        return KSerializerReader(self.read_exact(total - 2))

    def remaining(self) -> int:
        return len(self._stream.getvalue()) - self._stream.tell()

    def read_bytes(self, n: int) -> bytes:
        return self.read_exact(n)


def pixel_bytes(pixel_format: int) -> int:
    # Minimal mapping; unknown formats default to 1 byte/pixel.
    mapping = {0: 1, 1: 1, 2: 2, 3: 3, 4: 4}
    return mapping.get(pixel_format, 1)


def image_row_size(width: int, pixel_size: int, color_filter: int, pixel_format: int) -> int:
    if pixel_size == 0 and color_filter == 0:
        return int(math.ceil(width * pixel_bytes(pixel_format)))
    return width * pixel_size


def read_gdp_packet(sock: socket.socket) -> tuple[int, bytes]:
    header = _recv_exact(sock, 4)
    total = struct.unpack("<I", header)[0]
    rest = _recv_exact(sock, total - 4)
    packet = header + rest
    msg_type = struct.unpack_from("<H", rest, 0)[0]
    return msg_type, packet


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    chunks: list[bytes] = []
    got = 0
    while got < n:
        part = sock.recv(n - got)
        if not part:
            raise EOFError("GDP connection closed")
        chunks.append(part)
        got += len(part)
    return b"".join(chunks)
