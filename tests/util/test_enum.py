from __future__ import annotations

import pytest

from deebot_client.util.enum import IntEnumWithXml, StrEnumWithXml


class _TestStrEnumWithXml(StrEnumWithXml):
    """Simple Enum for testing."""

    ENUM1 = "value1", "xmlvalue1"
    ENUM2 = "value2", "xmlvalue2"


class _TestIntEnumWithXml(IntEnumWithXml):
    ENUM1 = 1, "xmlvalue1"
    ENUM2 = 2, "xmlvalue2"


@pytest.mark.parametrize(
    ("test_enum", "test_value", "test_xml_value"),
    [
        (_TestStrEnumWithXml.ENUM1, "value1", "xmlvalue1"),
        (_TestStrEnumWithXml.ENUM2, "value2", "xmlvalue2"),
    ],
)
def test_StrEnumWithXml_values(
    test_enum: _TestStrEnumWithXml, test_value: str, test_xml_value: str
) -> None:
    assert test_enum.value == test_value
    assert test_enum.xml_value == test_xml_value
    assert test_value == _TestStrEnumWithXml.from_xml(test_xml_value).value
    assert test_xml_value == _TestStrEnumWithXml(test_value).xml_value


def test_StrEnumWithXml_invalid_value() -> None:
    with pytest.raises(ValueError, match="this_is_invalid"):
        _TestStrEnumWithXml.from_xml("this_is_invalid")


@pytest.mark.parametrize(
    ("test_enum", "test_value", "test_xml_value"),
    [
        (_TestIntEnumWithXml.ENUM1, 1, "xmlvalue1"),
        (_TestIntEnumWithXml.ENUM2, 2, "xmlvalue2"),
    ],
)
def test_IntEnumWithXml_values(
    test_enum: _TestIntEnumWithXml, test_value: int, test_xml_value: str
) -> None:
    assert test_enum.value == test_value
    assert test_enum.xml_value == test_xml_value
    assert test_value == _TestIntEnumWithXml.from_xml(test_xml_value).value
    assert test_xml_value == _TestIntEnumWithXml(test_value).xml_value


def test_IntEnumWithXml_invalid_value() -> None:
    with pytest.raises(ValueError, match="this_is_invalid"):
        _TestIntEnumWithXml.from_xml("this_is_invalid")
