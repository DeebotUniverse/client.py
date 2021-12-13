from typing import Set, Type

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
