"""GoDiscoveryClient - mirrors GoPxLSdk::GoDiscoveryClient."""

from __future__ import annotations

import json
import socket
import struct
import time

from .classic_discovery import discover_classic, parse_get_info_reply, parse_get_ip_reply, send_get_info
from .classic_discovery import GET_IP_REPLY_SIZE
from .def_ import DISCOVERY_UDP_PORT
from .instance import GoInstance

GOPXL_DISCOVERY_SIGNATURE = 0x4C58504F47494D4C
GOPXL_DISCOVERY_MESSAGE_DISCOVER = 0x0001
GOPXL_DISCOVERY_MESSAGE_ANNOUNCE = 0x1001


class GoDiscoveryClient:
    def __init__(self) -> None:
        self._instances: list[GoInstance] = []
        self._gopxl_instances: list[GoInstance] = []
        self._classic_instances: list[GoInstance] = []

    def blocking_discover(self, timeout_ms: int = 3000, classic_discover: bool = False) -> None:
        self._instances.clear()
        self._gopxl_instances.clear()
        self._classic_instances.clear()

        self._discover_gopxl(timeout_ms)
        if classic_discover:
            self._discover_classic(timeout_ms)

        self._instances = list(self._gopxl_instances) + list(self._classic_instances)

    def _discover_gopxl(self, timeout_ms: int) -> None:
        header = struct.pack("<QQQ", 24, GOPXL_DISCOVERY_MESSAGE_DISCOVER, GOPXL_DISCOVERY_SIGNATURE)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.25)
        found: dict[tuple[str, int], GoInstance] = {}
        try:
            sock.bind(("", 0))
            sock.sendto(header, ("<broadcast>", DISCOVERY_UDP_PORT))
            end = time.monotonic() + timeout_ms / 1000.0
            while time.monotonic() < end:
                try:
                    data, _ = sock.recvfrom(4096)
                except socket.timeout:
                    continue
                except OSError:
                    break
                inst = self._parse_announce(data)
                if inst:
                    found[(inst.ip_address, inst.web_port)] = inst
        finally:
            sock.close()
        self._gopxl_instances = sorted(found.values(), key=lambda i: i.ip_address)

    def _discover_classic(self, timeout_ms: int) -> None:
        self._classic_instances = discover_classic(timeout_ms)

    def instance_list(self) -> list[GoInstance]:
        return self._instances

    def gopxl_instance_list(self) -> list[GoInstance]:
        return self._gopxl_instances

    def classic_instance_list(self) -> list[GoInstance]:
        return self._classic_instances

    def instance(self, ip_address: str, web_port: int) -> GoInstance | None:
        for inst in self._instances:
            if inst.ip_address == ip_address and inst.web_port == web_port:
                return inst
        return None

    def gopxl_instance(self, ip_address: str, web_port: int) -> GoInstance | None:
        for inst in self._gopxl_instances:
            if inst.ip_address == ip_address and inst.web_port == web_port:
                return inst
        return None

    def classic_instance(self, serial_number: int) -> GoInstance | None:
        for inst in self._classic_instances:
            if str(inst.serial_number) == str(serial_number):
                return inst
        return None

    def parse_reply(self, data: bytes) -> None:
        if len(data) == GET_IP_REPLY_SIZE:
            inst = parse_get_ip_reply(data)
            if inst is None:
                return
            serial = int(inst.serial_number)
            if any(str(i.serial_number) == str(serial) for i in self._classic_instances):
                return
            self._classic_instances.append(inst)
            self._instances.append(inst)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            try:
                send_get_info(sock, serial)
            finally:
                sock.close()
            return

        pending = {int(i.serial_number): i for i in self._classic_instances}
        inst = parse_get_info_reply(data, pending)
        if inst is None:
            gopxl = self._parse_announce(data)
            if gopxl is None:
                return
            key = (gopxl.ip_address, gopxl.web_port)
            if not any(i.ip_address == key[0] and i.web_port == key[1] for i in self._gopxl_instances):
                self._gopxl_instances.append(gopxl)
                self._instances.append(gopxl)
            return

        for idx, existing in enumerate(self._classic_instances):
            if str(existing.serial_number) == str(inst.serial_number):
                self._classic_instances[idx] = inst
                break

    @staticmethod
    def _parse_announce(data: bytes) -> GoInstance | None:
        if len(data) < 32:
            return None
        _length, message_id, signature = struct.unpack_from("<QQQ", data, 0)
        if message_id != GOPXL_DISCOVERY_MESSAGE_ANNOUNCE or signature != GOPXL_DISCOVERY_SIGNATURE:
            return None
        try:
            text = data[32:].decode("utf-8", errors="replace").rstrip("\x00")
            payload = json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return GoInstance.from_announce(payload)
