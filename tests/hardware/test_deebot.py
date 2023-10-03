"""Hardware deebot tests."""


from deebot_client.hardware.deebot import DEVICES

from . import verify_sorted_devices


def test_sorted() -> None:
    """Test if all devices are sorted correctly."""
    verify_sorted_devices(DEVICES)
