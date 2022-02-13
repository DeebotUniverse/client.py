from typing import Any, Optional, Set, Type

from deebot_client.util import DisplayNameIntEnum


def verify_DisplayNameEnum_unique(enum: type[DisplayNameIntEnum]):
    assert issubclass(enum, DisplayNameIntEnum)
    names: set[str] = set()
    values: set[int] = set()
    for member in enum:
        assert member.value not in values
        values.add(member.value)

        name = member.name.lower()
        assert name not in names
        names.add(name)

        display_name = member.display_name.lower()
        if display_name != name:
            assert display_name not in names
            names.add(display_name)


def get_request_json(data: Optional[dict[str, Any]]) -> dict[str, Any]:
    return {"id": "ALZf", "ret": "ok", "resp": get_message_json(data)}


def get_message_json(data: Optional[dict[str, Any]]) -> dict[str, Any]:
    json = {
        "header": {
            "pri": 1,
            "tzm": 480,
            "ts": "1304623069888",
            "ver": "0.0.1",
            "fwVer": "1.8.2",
            "hwVer": "0.1.1",
        },
        "body": {
            "code": 0,
            "msg": "ok",
        },
    }
    if data:
        json["body"]["data"] = data
    return json
