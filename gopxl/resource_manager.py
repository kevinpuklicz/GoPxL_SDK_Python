"""GoResourceManager - URI-keyed GoResource cache."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from .resource import GoResource

if TYPE_CHECKING:
    from .rest_client import GoRestClient


class GoResourceManager:
    def __init__(self, client: GoRestClient) -> None:
        self._client = client
        self._resources: dict[str, GoResource] = {}
        self._lock = threading.Lock()
        self._auto_subscribe = False
        self._auto_validation = False
        self._subscription_optimized_invalidation = True

    def get_or_create(self, uri: str) -> GoResource:
        key = uri if uri.startswith("/") else f"/{uri}"
        with self._lock:
            resource = self._resources.get(key)
            if resource is None:
                resource = GoResource(self._client, key, manager=self)
                self._resources[key] = resource
                if self._auto_subscribe:
                    resource.subscribe()
        return resource

    def set_auto_subscribe(self, enabled: bool) -> None:
        self._auto_subscribe = enabled

    def auto_subscribe(self) -> bool:
        return self._auto_subscribe

    def set_auto_validation(self, enabled: bool) -> None:
        self._auto_validation = enabled

    def auto_validation(self) -> bool:
        return self._auto_validation

    def set_subscription_optimized_invalidation(self, enabled: bool) -> None:
        self._subscription_optimized_invalidation = enabled

    def subscribe_all(self) -> None:
        with self._lock:
            resources = list(self._resources.values())
        for resource in resources:
            if not resource.is_subscribed():
                resource.subscribe()

    def unsubscribe_all(self) -> None:
        with self._lock:
            resources = list(self._resources.values())
        for resource in resources:
            if resource.is_subscribed():
                resource.unsubscribe()

    def invalidate_all(self) -> None:
        with self._lock:
            resources = list(self._resources.values())
        for resource in resources:
            if self._subscription_optimized_invalidation and resource.is_subscribed():
                continue
            resource.invalidate()

    def clear(self) -> None:
        with self._lock:
            self._resources.clear()
