"""Enum util."""

from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import Self


class StrEnumWithXml(StrEnum):
    """String enum with xml value."""

    xml_value: str | None

    def __new__(cls, value: str, xml_value: str | None = None) -> Self:
        """Create new StrEnumWithXml."""
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.xml_value = xml_value
        return obj

    @classmethod
    def from_xml(cls, value: str | None) -> Self:
        """Convert from xml value."""
        if value:
            for member in cls:
                if member.xml_value == value:
                    return member

        msg = f"{value} is not a valid {cls.__name__}"
        raise ValueError(msg)


class IntEnumWithXml(IntEnum):
    """Int enum with xml value."""

    xml_value: str | None

    def __new__(cls, value: int, xml_value: str | None = None) -> Self:
        """Create new StrEnumWithXml."""
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.xml_value = xml_value
        return obj

    @classmethod
    def from_xml(cls, value: str | None) -> Self:
        """Convert from xml value."""
        if value:
            for member in cls:
                if member.xml_value == value:
                    return member

        msg = f"{value} is not a valid {cls.__name__}"
        raise ValueError(msg)
