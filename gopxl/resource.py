"""GoResource - lightweight REST resource helper."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any, Callable

from .enums import GoNotificationType

if TYPE_CHECKING:
    from .resource_manager import GoResourceManager
    from .rest_client import GoRestClient
    from .response import GoNotificationResponse


class GoRelationType:
    Item = "item"
    Scanner = "go:scanner"
    SubTask = "go:subTask"
    Content = "go:content"
    Command = "go:command"
    Action = "go:action"


class GoResource:
    DEFAULT_TIMEOUT_MS = 5000
    DEFAULT_EXPAND_LEVEL = 0

    def __init__(
        self,
        client: GoRestClient,
        uri: str,
        manager: GoResourceManager | None = None,
    ) -> None:
        self._client = client
        self._uri = uri if uri.startswith("/") else f"/{uri}"
        self._manager = manager
        self._timeout_ms = self.DEFAULT_TIMEOUT_MS
        self._expand_level = self.DEFAULT_EXPAND_LEVEL
        self._cached_data: dict[str, Any] | None = None
        self._cache_valid = False
        self._pending_patch: dict[str, Any] = {}
        self._deferred_depth = 0
        self._has_remote_changes = False
        self._subscribed = False
        self._listener_id = 0
        self._change_handler: Callable[[GoNotificationResponse], None] | None = None

    def uri(self) -> str:
        return self._uri

    def set_timeout(self, timeout_ms: int) -> None:
        self._timeout_ms = timeout_ms

    def set_expand_level(self, level: int) -> None:
        self._expand_level = level

    def invalidate(self) -> None:
        self._cache_valid = False
        self._has_remote_changes = True

    def has_remote_changes(self) -> bool:
        return self._has_remote_changes

    def data(self, force_refresh: bool = False) -> dict[str, Any]:
        if force_refresh or not self._cache_valid:
            self.read()
        return copy.deepcopy(self._cached_data or {})

    def read(self) -> dict[str, Any]:
        response = self._client.read(self._uri, args={"expandLevel": self._expand_level}).get_response(
            self._timeout_ms
        )
        self._cached_data = dict(response.payload or {})
        self._cache_valid = True
        self._has_remote_changes = False
        return copy.deepcopy(self._cached_data)

    def update(self, patch: dict[str, Any] | None = None) -> dict[str, Any]:
        body = patch if patch is not None else self._pending_patch
        response = self._client.update(self._uri, body).get_response(self._timeout_ms)
        if isinstance(response.payload, dict):
            self._cached_data = dict(response.payload)
            self._cache_valid = True
        else:
            self.invalidate()
        self._pending_patch = {}
        self._has_remote_changes = False
        return copy.deepcopy(self._cached_data or {})

    def call_command(self, command_uri: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        uri = command_uri if command_uri.startswith("/") else f"{self._uri}/{command_uri}"
        response = self._client.call(uri, payload or {}).get_response(self._timeout_ms)
        self.invalidate()
        return dict(response.payload or {})

    def begin_update(self) -> None:
        self._deferred_depth += 1

    def end_update(self) -> dict[str, Any]:
        if self._deferred_depth <= 0:
            raise RuntimeError("end_update without begin_update")
        self._deferred_depth -= 1
        if self._deferred_depth == 0 and self._pending_patch:
            return self.update()
        return self.data()

    def set_value(self, key: str, value: Any) -> None:
        if self._deferred_depth > 0:
            self._pending_patch[key] = value
        else:
            self.update({key: value})

    def get_value(self, key: str, default: Any = None) -> Any:
        payload = self.data()
        return payload.get(key, default)

    def child_uris(self, relation_type: str = GoRelationType.Item) -> list[str]:
        payload = self.data()
        links = payload.get("_links") or {}
        rel = links.get(relation_type) or []
        if isinstance(rel, dict):
            rel = [rel]
        uris: list[str] = []
        for item in rel:
            if isinstance(item, dict):
                href = item.get("href")
                if href:
                    uris.append(str(href))
        return uris

    def children(self, relation_type: str = GoRelationType.Item) -> list[GoResource]:
        from .resource_manager import GoResourceManager

        mgr = self._manager or GoResourceManager(self._client)
        return [mgr.get_or_create(uri) for uri in self.child_uris(relation_type)]

    def child(self, relation_type: str, index: int = 0) -> GoResource | None:
        uris = self.child_uris(relation_type)
        if index < 0 or index >= len(uris):
            return None
        from .resource_manager import GoResourceManager

        mgr = self._manager or GoResourceManager(self._client)
        return mgr.get_or_create(uris[index])

    def subscribe(self, change_handler: Callable[[GoNotificationResponse], None] | None = None) -> None:
        if self._subscribed:
            return
        self._change_handler = change_handler

        def _on_notification(notification: GoNotificationResponse) -> None:
            if notification.path != self._uri:
                return
            if notification.notification_type in (
                GoNotificationType.UPDATED,
                GoNotificationType.EMBEDDED_UPDATED,
            ):
                if isinstance(notification.payload, dict):
                    self._cached_data = dict(notification.payload)
                    self._cache_valid = True
                else:
                    self.invalidate()
            elif notification.notification_type == GoNotificationType.DELETED:
                self._cache_valid = False
                self._cached_data = None
            if self._change_handler is not None:
                self._change_handler(notification)

        self._listener_id = self._client.add_notification_listener(self._uri, _on_notification)
        self._client.sub(self._uri).check_response(self._timeout_ms)
        self._subscribed = True

    def unsubscribe(self) -> None:
        if not self._subscribed:
            return
        try:
            self._client.unsub(self._uri).check_response(self._timeout_ms)
        finally:
            if self._listener_id:
                self._client.remove_notification_listener(self._listener_id)
            self._listener_id = 0
            self._subscribed = False
            self._change_handler = None

    def is_subscribed(self) -> bool:
        return self._subscribed
