from __future__ import annotations

from typing import Any


def get_request_xml(data: str | None) -> dict[str, Any]:
    return {"id": "ALZf", "ret": "ok", "resp": data, "payloadType": "x"}
