from __future__ import annotations

from typing import Any, Protocol


class RiotHttpClient(Protocol):
    def get_json(self, *, url: str, params: dict | None = None) -> Any: ...
