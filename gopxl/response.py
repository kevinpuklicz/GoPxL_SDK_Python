"""GoResponse hierarchy - mirrors GoPxLSdk response types."""

from __future__ import annotations

from dataclasses import dataclass

from .enums import GoNotificationType, GoResponseType, GoStatus


@dataclass(slots=True)
class GoResponse:
    status: GoStatus
    type: GoResponseType
    path: str
    payload: dict
    raw: dict

    @classmethod
    def from_wire(cls, raw: dict) -> GoResponse:
        rtype = str(raw.get("type", "request")).lower()
        if rtype == "notification":
            return GoNotificationResponse.from_wire(raw)
        if rtype == "stream":
            return GoStreamResponse.from_wire(raw)
        return GoRequestResponse.from_wire(raw)


@dataclass(slots=True)
class GoRequestResponse(GoResponse):
    @classmethod
    def from_wire(cls, raw: dict) -> GoRequestResponse:
        return cls(
            status=GoStatus(int(raw.get("status", 0))),
            type=GoResponseType.REQUEST,
            path=str(raw.get("path", "")),
            payload=raw.get("payload") or {},
            raw=raw,
        )


@dataclass(slots=True)
class GoNotificationResponse(GoResponse):
    notification_type: GoNotificationType = GoNotificationType.UPDATED

    @classmethod
    def from_wire(cls, raw: dict) -> GoNotificationResponse:
        event = str(raw.get("eventType", "updated"))
        try:
            ntype = GoNotificationType[event.upper()]
        except KeyError:
            ntype = GoNotificationType.UPDATED
        return cls(
            status=GoStatus(int(raw.get("status", 0))),
            type=GoResponseType.NOTIFICATION,
            path=str(raw.get("path", "")),
            payload=raw.get("payload") or {},
            raw=raw,
            notification_type=ntype,
        )


@dataclass(slots=True)
class GoStreamResponse(GoResponse):
    stream_identifier: int = 0
    stream_status: str = ""

    @classmethod
    def from_wire(cls, raw: dict) -> GoStreamResponse:
        return cls(
            status=GoStatus(int(raw.get("status", 0))),
            type=GoResponseType.STREAM,
            path=str(raw.get("path", "")),
            payload=raw.get("payload") or {},
            raw=raw,
            stream_identifier=int(raw.get("streamId", 0)),
            stream_status=str(raw.get("streamStatus", "")),
        )
