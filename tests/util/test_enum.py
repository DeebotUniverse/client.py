from __future__ import annotations

import pytest

from deebot_client.util.enum import IntEnumWithXml, StrEnumWithXml


class _TestStrEnumWithXml(StrEnumWithXml):
    ENUM1 = "value1", "xmlvalue1"
    ENUM2 = "value2", "xmlvalue2"

    def assert_self_conversion(self) -> None:
        assert self == _TestStrEnumWithXml(self.value)
        assert self == _TestStrEnumWithXml.from_xml(self.xml_value)


class _TestIntEnumWithXml(IntEnumWithXml):
    ENUM1 = 1, "xmlvalue1"
    ENUM2 = 2, "xmlvalue2"

    def assert_self_conversion(self) -> None:
        assert self == _TestIntEnumWithXml(self.value)
        assert self == _TestIntEnumWithXml.from_xml(self.xml_value)


@pytest.mark.parametrize(
    "test_enum", list(_TestStrEnumWithXml) + list(_TestIntEnumWithXml)
)
def test_EnumWithXml_conversion[T: (_TestStrEnumWithXml, _TestIntEnumWithXml)](
    test_enum: T,
) -> None:
    test_enum.assert_self_conversion()


@pytest.mark.parametrize(
    ("test_enum_cls", "invalid_value"),
    [
        (_TestStrEnumWithXml, "this_is_invalid"),
        (_TestStrEnumWithXml, None),
        (_TestIntEnumWithXml, "this_is_invalid"),
        (_TestIntEnumWithXml, None),
    ],
)
def test_EnumWithXml_invalid_value[T: (_TestStrEnumWithXml, _TestIntEnumWithXml)](
    test_enum_cls: type[T], invalid_value: str | None
) -> None:
    with pytest.raises(ValueError, match=str(invalid_value)):
        test_enum_cls.from_xml(invalid_value)
