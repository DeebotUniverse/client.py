"""Common xml based commands."""


from xml.etree import ElementTree

from deebot_client.command import Command
from deebot_client.const import DataType


class XmlCommand(Command):
    """Xml command."""

    data_type: DataType = DataType.XML

    @property
    @classmethod
    def has_sub_element(self) -> bool:
        """Return True if command has inner element."""
        return False

    def _get_payload(self) -> str:
        element = ctl_element = ElementTree.Element("ctl")

        if len(self._args) > 0:
            if self.has_sub_element:
                element = ElementTree.SubElement(element, self.name.lower())

            for key in self._args:
                element.set(key, self._args[key])

        return ElementTree.tostring(ctl_element, "unicode")
