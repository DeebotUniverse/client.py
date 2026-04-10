from __future__ import annotations

from unittest.mock import Mock

from unittest.mock import AsyncMock

from deebot_client.mqtt_client import MqttClient, MqttConfiguration, SubscriberInfo, _get_topics


def test_get_topics_adds_ngiot_user_topics(device_info) -> None:
    topics = _get_topics(device_info, "user-123")

    assert f"iot/atr/+/user-123/{device_info.api['class']}/{device_info.api['did']}/{device_info.static.data_type}" in topics
    assert f"iot/atr/+/user-123/{device_info.api['class']}/{device_info.api['resource']}/{device_info.static.data_type}" in topics
    assert len(topics) == len(set(topics))


def test_topic_matches_device_supports_legacy_and_ngiot_shapes(device_info) -> None:
    legacy = [
        "iot",
        "atr",
        "onBattery",
        device_info.api["did"],
        device_info.api["class"],
        device_info.api["resource"],
        str(device_info.static.data_type),
    ]
    ngiot_did = [
        "iot",
        "atr",
        "10000",
        "user-123",
        device_info.api["class"],
        device_info.api["did"],
        str(device_info.static.data_type),
    ]
    ngiot_resource = [
        "iot",
        "atr",
        "30000",
        "user-123",
        device_info.api["class"],
        device_info.api["resource"],
        str(device_info.static.data_type),
    ]

    assert MqttClient._topic_matches_device(legacy, device_info) is True
    assert MqttClient._topic_matches_device(ngiot_did, device_info) is True
    assert MqttClient._topic_matches_device(ngiot_resource, device_info) is True
    assert MqttClient._topic_matches_device(ngiot_resource[:-1] + ["x"], device_info) is False


def test_handle_atr_routes_numeric_ngiot_topics(authenticator, device_info, event_bus) -> None:
    config = MqttConfiguration(hostname="localhost", port=1883, ssl_context=None, device_id="test-device")
    authenticator.subscribe = AsyncMock()
    client = MqttClient(config, authenticator)
    callback = Mock()
    client._subscriptions[device_info.api["did"]] = SubscriberInfo(
        device_info=device_info,
        events=event_bus,
        callback=callback,
    )

    client._handle_atr(
        [
            "iot",
            "atr",
            "30000",
            "user-123",
            device_info.api["class"],
            device_info.api["resource"],
            str(device_info.static.data_type),
        ],
        b'{"body":{"data":{"status":"smartclean"}}}',
    )

    callback.assert_called_once_with(
        "30000", b'{"body":{"data":{"status":"smartclean"}}}'
    )
