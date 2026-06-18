"""GoInstance - mirrors GoPxLSdk::GoInstance."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class GoInstance:
    ip_address: str
    control_port: int = 3600
    web_port: int = 8100
    gdp_port: int = 3601
    app_id: str = ""
    app_name: str = ""
    app_version: str = ""
    serial_number: str = ""
    device_model: str = ""
    is_dhcp: bool = False
    is_remote: bool = False
    is_address_conflict: bool = False
    gateway: str = ""
    mask: str = ""
    hmi_status: int = 0
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_announce(cls, payload: dict) -> GoInstance | None:
        address = payload.get("Address")
        if not address:
            return None
        serial = payload.get("SerialNumber", "")
        if isinstance(serial, (int, float)):
            serial = str(int(serial))
        return cls(
            ip_address=str(address),
            control_port=int(payload.get("ControlPort") or 3600),
            web_port=int(payload.get("WebPort") or 8100),
            gdp_port=int(payload.get("GdpPort") or 3601),
            app_id=str(payload.get("AppId") or ""),
            app_name=str(payload.get("AppName") or ""),
            app_version=str(payload.get("AppVersion") or ""),
            serial_number=str(serial),
            device_model=str(payload.get("DeviceModel") or ""),
            is_dhcp=bool(payload.get("Dhcp")),
            is_remote=bool(payload.get("IsRemote")),
            is_address_conflict=bool(payload.get("AddressConflict")),
            gateway=str(payload.get("Gateway") or ""),
            mask=str(payload.get("Mask") or ""),
            hmi_status=int(payload.get("HMIStatus") or 0),
            raw=payload,
        )

    def get_ip_address(self) -> str:
        return self.ip_address

    def get_control_port(self) -> int:
        return self.control_port

    def get_web_port(self) -> int:
        return self.web_port

    def get_gdp_port(self) -> int:
        return self.gdp_port

    def get_is_remote(self) -> bool:
        return self.is_remote
