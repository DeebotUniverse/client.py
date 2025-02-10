from __future__ import annotations

import pytest

from deebot_client.util.enum import StrEnumWithXml


class TestStrEnumWithXml(StrEnumWithXml):
    """Simple Enum for testing."""

    ENUM1 = "value1", "xmlvalue1"
    ENUM2 = "value2", "xmlvalue2"


@pytest.mark.parametrize(
    ("test_enum", "test_value", "test_xml_value"),
    [
        (TestStrEnumWithXml.ENUM1, "value1", "xmlvalue1"),
        (TestStrEnumWithXml.ENUM2, "value2", "xmlvalue2"),
    ],
)
def test_StrEnumWithXml_values(
    test_enum: TestStrEnumWithXml, test_value: str, test_xml_value: str
) -> None:
    assert test_enum.value == test_value
    assert test_enum.xml_value == test_xml_value
    assert test_value == TestStrEnumWithXml.from_xml(test_xml_value).value
    assert test_xml_value == TestStrEnumWithXml(test_value).xml_value

    # test ENUM from invalid xml
    try:
        TestStrEnumWithXml.from_xml("this_is_invalid")
        raise AssertionError
    except ValueError:
        assert True
