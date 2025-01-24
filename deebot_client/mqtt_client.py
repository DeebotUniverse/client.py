"""MQTT module."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
import json
import ssl
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from aiomqtt import Client, Message, MqttError as AioMqttError
from cachetools import TTLCache

from deebot_client.const import UNDEFINED, DataType, UndefinedType
from deebot_client.exceptions import AuthenticationError, MqttError

from .commands import COMMANDS_WITH_MQTT_P2P_HANDLING
from .logging_filter import get_logger
from .util.continents import get_continent_url_postfix

if TYPE_CHECKING:
    from collections.abc import Callable, MutableMapping

    from .authentication import Authenticator
    from .command import CommandMqttP2P
    from .event_bus import EventBus
    from .models import Credentials, DeviceInfo

RECONNECT_INTERVAL = 5  # seconds

_LOGGER = get_logger(__name__)
_CLIENT_LOGGER = get_logger(f"{__name__}.client")


def _get_topics(device_info: DeviceInfo) -> list[str]:
    api = device_info.api
    device_path = f"{api['did']}/{api['class']}/{api['resource']}"
    data_type = device_info.static.data_type
    return [
        # iot/atr/[command]]/[did]]/[class]]/[resource]/j
        f"iot/atr/+/{device_path}/{data_type}",
        # iot/p2p/[command]]/[sender did]/[sender class]]/[sender resource]
        # /[receiver did]/[receiver class]]/[receiver resource]/[q|p]/[request id]/j
        # [q|p] q-> request p-> response
        f"iot/p2p/+/+/+/+/{device_path}/q/+/{data_type}",
        f"iot/p2p/+/{device_path}/+/+/+/p/+/{data_type}",
    ]


@dataclass(frozen=True, kw_only=True)
class MqttConfiguration:
    """Mqtt configuration."""

    hostname: str
    port: int
    ssl_context: ssl.SSLContext | None
    device_id: str


def create_mqtt_config(
    *,
    device_id: str,
    country: str,
    override_mqtt_url: str | None = None,
    ssl_context: ssl.SSLContext | None | UndefinedType = UNDEFINED,
) -> MqttConfiguration:
    """Create configuration."""
    continent_postfix = get_continent_url_postfix(country.upper())
    ssl_ctx = None if ssl_context is UNDEFINED else ssl_context

    if override_mqtt_url:
        url = urlparse(override_mqtt_url)
        match url.scheme:
            case "mqtt":
                default_port = 1883
            case "mqtts":
                default_port = 8883
                if ssl_context is UNDEFINED:
                    ssl_ctx = ssl.create_default_context()
            case _:
                raise MqttError("Invalid scheme. Expecting mqtt or mqtts")

        if not url.hostname:
            raise MqttError("Hostname is required")

        hostname = url.hostname
        port = url.port or default_port
    else:
        hostname = f"mq{continent_postfix}.ecouser.net"
        port = 443
        if ssl_context is UNDEFINED:
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE

    return MqttConfiguration(
        hostname=hostname,
        port=port,
        ssl_context=ssl_ctx,
        device_id=device_id,
    )


@dataclass(frozen=True)
class SubscriberInfo:
    """Subscriber information."""

    device_info: DeviceInfo
    events: EventBus
    callback: Callable[[str, str | bytes | bytearray], None]


class MqttClient:
    """MQTT client."""

    def __init__(
        self,
        config: MqttConfiguration,
        authenticator: Authenticator,
    ) -> None:
        self._config = config
        self._authenticator = authenticator

        self._subscriptions: MutableMapping[str, SubscriberInfo] = {}
        self._subscription_changes: asyncio.Queue[tuple[SubscriberInfo, bool]] = (
            asyncio.Queue()
        )
        self._mqtt_task: asyncio.Task[Any] | None = None

        self._received_p2p_commands: MutableMapping[str, CommandMqttP2P] = TTLCache(
            maxsize=60 * 60, ttl=60
        )
        self._last_message_received_at: datetime | None = None

        async def on_credentials_changed(_: Credentials) -> None:
            await self._create_mqtt_task()

        authenticator.subscribe(on_credentials_changed)

    @property
    def last_message_received_at(self) -> datetime | None:
        """Return the datetime of the last received message or None."""
        return self._last_message_received_at

    async def verify_config(self) -> None:
        """Verify config by connecting to the broker."""
        try:
            async with await self._get_client():
                _LOGGER.debug("Connection successfully")
        except AioMqttError as ex:
            _LOGGER.warning("Cannot connect", exc_info=True)
            raise MqttError("Cannot connect") from ex

    async def subscribe(self, info: SubscriberInfo) -> Callable[[], None]:
        """Subscribe for messages from given device."""
        await self.connect()
        self._subscription_changes.put_nowait((info, True))

        def unsubscribe() -> None:
            self._subscription_changes.put_nowait((info, False))

        return unsubscribe

    async def connect(self) -> None:
        """Connect to MQTT."""
        if self._mqtt_task is None or self._mqtt_task.done():
            # call authenticator to verify that we have valid credentials
            await self._authenticator.authenticate()

            await self._create_mqtt_task()

    async def disconnect(self) -> None:
        """Disconnect from MQTT."""
        await self._cancel_mqtt_task()

    async def _get_client(self) -> Client:
        credentials = await self._authenticator.authenticate()
        client_id = f"{credentials.user_id}@ecouser/{self._config.device_id}"
        return Client(
            hostname=self._config.hostname,
            port=self._config.port,
            username=credentials.user_id,
            password=credentials.token,
            logger=_CLIENT_LOGGER,
            identifier=client_id,
            tls_context=self._config.ssl_context,
        )

    async def _cancel_mqtt_task(self) -> None:
        if self._mqtt_task is not None and self._mqtt_task.cancel():
            # Wait for the task to be cancelled
            with suppress(asyncio.CancelledError):
                await self._mqtt_task

    async def _create_mqtt_task(self) -> None:
        async def mqtt() -> None:
            while True:
                try:
                    async with await self._get_client() as client:
                        _LOGGER.debug("Subscribe to all previous subscriptions")
                        for info in self._subscriptions.values():
                            for topic in _get_topics(info.device_info):
                                await client.subscribe(topic)

                        async def listen() -> None:
                            async for message in client.messages:
                                self._handle_message(message)

                        tasks = [
                            asyncio.create_task(listen()),
                            asyncio.create_task(
                                self._pending_subscriptions_worker(client)
                            ),
                        ]
                        try:
                            _LOGGER.debug("All mqtt tasks created")
                            await asyncio.wait(
                                tasks, return_when=asyncio.FIRST_COMPLETED
                            )
                        finally:
                            for task in tasks:
                                task.cancel()
                except AioMqttError:
                    _LOGGER.warning(
                        "Connection lost; Reconnecting in %d seconds ...",
                        RECONNECT_INTERVAL,
                        exc_info=True,
                    )
                except AuthenticationError:
                    _LOGGER.exception(
                        "Could not authenticate. Please check your credentials and afterwards reload the integration."
                    )
                    return
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("An exception occurred")
                    return

                await asyncio.sleep(RECONNECT_INTERVAL)

        await self._cancel_mqtt_task()
        self._mqtt_task = asyncio.create_task(mqtt())

    def _handle_message(self, message: Message) -> None:
        _LOGGER.debug(
            "Got message: topic=%s, payload=%s", message.topic, message.payload
        )
        self._last_message_received_at = datetime.now()

        if message.payload is None or isinstance(message.payload, int | float):
            _LOGGER.warning(
                "Unexpected message: topic=%s, payload=%s",
                message.topic,
                message.payload,
            )
            return

        topic_split = message.topic.value.split("/")
        if message.topic.matches("iot/atr/#"):
            self._handle_atr(topic_split, message.payload)
        elif message.topic.matches("iot/p2p/#"):
            self._handle_p2p(topic_split, message.payload)
        else:
            _LOGGER.debug("Got unsupported topic: %s", message.topic)

    async def _pending_subscriptions_worker(self, client: Client) -> None:
        while True:
            (info, add) = await self._subscription_changes.get()

            device_info = info.device_info
            for topic in _get_topics(device_info):
                if add:
                    await client.subscribe(topic)
                else:
                    await client.unsubscribe(topic)

            if add:
                self._subscriptions[device_info.api["did"]] = info
            else:
                self._subscriptions.pop(device_info.api["did"], None)

            self._subscription_changes.task_done()

    def _handle_atr(
        self, topic_split: list[str], payload: str | bytes | bytearray
    ) -> None:
        try:
            if sub_info := self._subscriptions.get(topic_split[3]):
                sub_info.callback(topic_split[2], payload)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("An exception occurred during handling atr message")

    def _handle_p2p(
        self, topic_split: list[str], payload: str | bytes | bytearray
    ) -> None:
        try:
            if (data_type := DataType.get(topic_split[11])) is None:
                _LOGGER.warning('Unsupported data type: "%s"', topic_split[11])
                return

            command_name = topic_split[2]
            command_type = COMMANDS_WITH_MQTT_P2P_HANDLING.get(data_type, {}).get(
                command_name, None
            )
            if command_type is None:
                _LOGGER.debug(
                    "Command %s does not support p2p handling (yet)", command_name
                )
                return

            is_request = topic_split[9] == "q"
            request_id = topic_split[10]

            if is_request:
                payload_json = json.loads(payload)
                try:
                    data = payload_json["body"]["data"]
                except KeyError:
                    _LOGGER.warning(
                        "Could not parse p2p payload: topic=%s; payload=%s",
                        "/".join(topic_split),
                        payload_json,
                    )
                    return

                self._received_p2p_commands[request_id] = command_type.create_from_mqtt(
                    data
                )
            elif command := self._received_p2p_commands.pop(request_id, None):
                if sub_info := self._subscriptions.get(topic_split[3]):
                    data = json.loads(payload)
                    command.handle_mqtt_p2p(sub_info.events, data)
            else:
                _LOGGER.debug(
                    "Response to command came in probably to late. requestId=%s, commandName=%s",
                    request_id,
                    command_name,
                )
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("An exception occurred during handling p2p message")
