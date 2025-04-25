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
    def _from_xml(cls, value: str | None) -> Self | None:
        """Convert from xml value, returning None if the value is not supported."""
        if value:
            for member in cls:
                if member.xml_value == value:
                    return member
        return None

    @classmethod
    def is_valid_xml_value(cls, value: str | None) -> bool:
        """Convert from xml value."""
        result = cls._from_xml(value)
        return result is not None

    @classmethod
    def from_xml(cls, value: str | None) -> Self:
        """Convert from xml value."""
        result = cls._from_xml(value)
        if result is not None:
            return result

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
    def _from_xml(cls, value: str | None) -> Self | None:
        """Convert from xml value, returning None if the value is not supported."""
        if value:
            for member in cls:
                if member.xml_value == value:
                    return member
        return None

    @classmethod
    def is_valid_xml_value(cls, value: str | None) -> bool:
        """Convert from xml value."""
        result = cls._from_xml(value)
        return result is not None

    @classmethod
    def from_xml(cls, value: str | None) -> Self:
        """Convert from xml value."""
        result = cls._from_xml(value)
        if result is not None:
            return result

        msg = f"{value} is not a valid {cls.__name__}"
        raise ValueError(msg)
