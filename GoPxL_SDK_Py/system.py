"""GoSystem - mirrors GoPxLSdk::GoSystem."""

from __future__ import annotations

from typing import Callable

from .def_ import DEFAULT_CONTROL_PORT, DEFAULT_TRANSACTION_TIMEOUT_MSEC
from .enums import GoSystemState
from .exceptions import GoRequestError
from .instance import GoInstance
from .resource import GoResource
from .resource_manager import GoResourceManager
from .rest_client import GoRestClient

GDP_TIMEOUT_MSEC = 15000
START_TIMEOUT_MSEC = 15000
STOP_TIMEOUT_MSEC = 15000
RUNNING_STATE_TIMEOUT_MSEC = 15000
QUICKEDIT_TIMEOUT_MSEC = 15000


class GoSystem:
    """High-level interface to a single Gocator / GoPxL system."""

    State = GoSystemState

    def __init__(self, address: str = "", control_port: int = DEFAULT_CONTROL_PORT) -> None:
        self._address = address
        self._control_port = control_port
        self._rest = GoRestClient()
        self._resource_manager = GoResourceManager(self._rest)
        self._disconnect_handler: Callable[[], None] | None = None

    @classmethod
    def from_instance(cls, instance: GoInstance) -> GoSystem:
        system = cls(instance.ip_address, instance.control_port or DEFAULT_CONTROL_PORT)
        return system

    def set_address(self, address: str) -> None:
        if not address:
            raise ValueError("address is required")
        self._address = address

    def address(self) -> str:
        return self._address

    def set_control_port(self, port: int) -> None:
        if not port:
            raise ValueError("port must be non-zero")
        self._control_port = port

    def control_port(self) -> int:
        return self._control_port

    def gdp_port(self) -> int:
        response = self._rest.read("/controls/gocator").get_response(GDP_TIMEOUT_MSEC)
        return int(response.payload.get("serverPort", 3601))

    def connect(self) -> None:
        if not self._address:
            raise GoRequestError("Address not set")
        self._rest.connect(self._address, self._control_port)

    def disconnect(self) -> None:
        self._rest.disconnect()

    def is_connected(self) -> bool:
        return self._rest.is_connected()

    def start(self) -> None:
        self._rest.call("/system/commands/start").check_response(START_TIMEOUT_MSEC)

    def stop(self) -> None:
        self._rest.call("/system/commands/stop").check_response(STOP_TIMEOUT_MSEC)

    def running_state(self) -> GoSystemState:
        response = self._rest.read("/system").get_response(RUNNING_STATE_TIMEOUT_MSEC)
        return GoSystemState(int(response.payload.get("runState", 0)))

    def enable_quick_edit(self) -> None:
        self._rest.update("/system", {"quickEditEnabled": True}).check_response(QUICKEDIT_TIMEOUT_MSEC)

    def disable_quick_edit(self) -> None:
        self._rest.update("/system", {"quickEditEnabled": False}).check_response(QUICKEDIT_TIMEOUT_MSEC)

    def quick_edit_enabled(self) -> bool:
        response = self._rest.read("/system").get_response(QUICKEDIT_TIMEOUT_MSEC)
        return bool(response.payload.get("quickEditEnabled"))

    def client(self) -> GoRestClient:
        return self._rest

    def resource_manager(self) -> GoResourceManager:
        return self._resource_manager

    def resource(self, uri: str) -> GoResource:
        return self._resource_manager.get_or_create(uri)

    def set_disconnect_handler(self, handler: Callable[[], None] | None) -> None:
        self._disconnect_handler = handler
        self._rest.set_disconnect_handler(handler)

    def sensor_path(self, serial_number: str) -> str:
        response = self._rest.read("/scan/visibleSensors/", args={"expandLevel": 1}).get_response(
            RUNNING_STATE_TIMEOUT_MSEC
        )
        sensors = response.payload.get("sensors") or []
        for sensor in sensors:
            if str(sensor.get("serialNumber", "")) == str(serial_number):
                return str(sensor.get("path", ""))
        return ""

    @property
    def web_gui_url(self) -> str:
        return f"http://{self._address}:8100/"

    def __enter__(self) -> GoSystem:
        self.connect()
        return self

    def __exit__(self, *args) -> None:
        self.disconnect()
