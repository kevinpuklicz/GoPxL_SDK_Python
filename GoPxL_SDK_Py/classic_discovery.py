"""Classic Gocator discovery protocol (UDP 3220) for legacy sensors."""

from __future__ import annotations

import socket
import struct
import time

from .instance import GoInstance
from .kserializer import KSerializerReader

CLASSIC_DISCOVERY_UDP_PORT = 3220
CLASSIC_BROADCAST_SIGNATURE = 0x0000504455494D4C
CLASSIC_DISCOVERY_COMMAND_GET_IP = 0x0001
CLASSIC_DISCOVERY_REPLY_GET_IP = 0x1001
CLASSIC_DISCOVERY_COMMAND_GET_INFO = 0x0005
CLASSIC_DISCOVERY_REPLY_GET_INFO = 0x1005
CLASSIC_DISCOVERY_OK_STATUS = 1
GET_IP_REPLY_SIZE = 84


def _byteswap32(value: int) -> int:
    return struct.unpack(">I", struct.pack("<I", value & 0xFFFFFFFF))[0]


def _ipv4_from_bytes(raw: bytes) -> str:
    host = _byteswap32(struct.unpack("<I", raw)[0])
    return socket.inet_ntoa(struct.pack(">I", host))


def broadcast_get_ip(sock: socket.socket) -> None:
    packet = struct.pack(
        "<QQQQ",
        24,
        CLASSIC_DISCOVERY_COMMAND_GET_IP,
        CLASSIC_BROADCAST_SIGNATURE,
        0,
    )
    sock.sendto(packet, ("<broadcast>", CLASSIC_DISCOVERY_UDP_PORT))


def send_get_info(sock: socket.socket, serial: int) -> None:
    packet = struct.pack(
        "<QQQQ",
        32,
        CLASSIC_DISCOVERY_COMMAND_GET_INFO,
        CLASSIC_BROADCAST_SIGNATURE,
        serial,
    )
    sock.sendto(packet, ("<broadcast>", CLASSIC_DISCOVERY_UDP_PORT))


def parse_get_ip_reply(data: bytes) -> GoInstance | None:
    if len(data) != GET_IP_REPLY_SIZE:
        return None
    length, message_id, status, signature, serial, is_dhcp = struct.unpack_from("<6q", data, 0)
    if (
        length != GET_IP_REPLY_SIZE
        or message_id != CLASSIC_DISCOVERY_REPLY_GET_IP
        or signature != CLASSIC_BROADCAST_SIGNATURE
        or status != CLASSIC_DISCOVERY_OK_STATUS
    ):
        return None
    offset = 48
    _reserved0 = data[offset : offset + 4]
    offset += 4
    address = data[offset : offset + 4]
    offset += 8
    mask = data[offset : offset + 4]
    offset += 8
    gateway = data[offset : offset + 4]
    return GoInstance(
        ip_address=_ipv4_from_bytes(address),
        mask=_ipv4_from_bytes(mask),
        gateway=_ipv4_from_bytes(gateway),
        serial_number=str(int(serial)),
        app_id=f"classic-{int(serial)}",
        app_name="Gocator Classic",
        is_dhcp=bool(is_dhcp),
    )


def parse_get_info_reply(data: bytes, pending: dict[int, GoInstance]) -> GoInstance | None:
    if len(data) < 32:
        return None
    reader = KSerializerReader(data)
    length = reader.read_i64()
    message_id = reader.read_i64()
    reply_status = reader.read_i64()
    signature = reader.read_i64()
    if (
        message_id != CLASSIC_DISCOVERY_REPLY_GET_INFO
        or signature != CLASSIC_BROADCAST_SIGNATURE
        or reply_status != 1
        or length != len(data)
    ):
        return None
    _attr_size = reader.read_u16()
    serial = reader.read_u32()
    version = reader.read_u32()
    _uptime = reader.read_u64()
    _dhcp = reader.read_u8()
    _address_version = reader.read_u8()
    _address = reader.read_bytes(4)
    _prefix = reader.read_u32()
    _gateway_version = reader.read_u8()
    _gateway = reader.read_bytes(4)
    control_port = reader.read_u16()
    _upgrade_port = reader.read_u16()
    _health_port = reader.read_u16()
    data_port = reader.read_u16()
    web_port = reader.read_u16()
    inst = pending.get(serial)
    if inst is None:
        return None
    inst.control_port = control_port
    inst.web_port = web_port
    inst.gdp_port = data_port
    inst.app_version = _format_version(version)
    return inst


def _format_version(version: int) -> str:
    major = (version >> 24) & 0xFF
    minor = (version >> 16) & 0xFF
    release = (version >> 8) & 0xFF
    build = version & 0xFF
    return f"{major}.{minor}.{release}.{build}"


def discover_classic(timeout_ms: int = 3000) -> list[GoInstance]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(0.25)
    pending: dict[int, GoInstance] = {}
    complete: dict[int, GoInstance] = {}
    try:
        sock.bind(("", CLASSIC_DISCOVERY_UDP_PORT))
    except OSError:
        sock.bind(("", 0))
    try:
        broadcast_get_ip(sock)
        end = time.monotonic() + timeout_ms / 1000.0
        while time.monotonic() < end:
            try:
                data, _ = sock.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            if len(data) == GET_IP_REPLY_SIZE:
                inst = parse_get_ip_reply(data)
                if inst is None:
                    continue
                serial = int(inst.serial_number)
                if serial in pending or serial in complete:
                    continue
                pending[serial] = inst
                send_get_info(sock, serial)
                continue
            inst = parse_get_info_reply(data, pending)
            if inst is None:
                continue
            serial = int(inst.serial_number)
            complete[serial] = inst
            pending.pop(serial, None)
    finally:
        sock.close()
    for serial, inst in pending.items():
        if serial not in complete:
            complete[serial] = inst
    return sorted(complete.values(), key=lambda i: i.ip_address)
