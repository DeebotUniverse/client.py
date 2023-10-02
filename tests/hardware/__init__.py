from collections.abc import Mapping

from deebot_client.hardware.device_capabilities import DeviceCapabilities


def verify_sorted_devices(devices: Mapping[str, DeviceCapabilities]) -> None:
    sorted_keys = sorted(devices.keys())
    assert sorted_keys == list(
        devices.keys()
    ), f"Devices expected to sort like {sorted_keys}"
