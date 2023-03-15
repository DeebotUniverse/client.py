"""MQTT module."""
import asyncio
import json
import ssl
from collections.abc import MutableMapping
from dataclasses import _MISSING_TYPE, InitVar, dataclass, field, fields
from datetime import datetime

from cachetools import TTLCache
from gmqtt import Client, Subscription
from gmqtt.mqtt.constants import MQTTv311

from .authentication import Authenticator
from .commands import COMMANDS_WITH_MQTT_P2P_HANDLING, CommandHandlingMqttP2P
from .exceptions import NotInitializedError
from .logging_filter import get_logger
from .models import Configuration, Credentials, DeviceInfo
from .vacuum_bot import VacuumBot

_LOGGER = get_logger(__name__)


def _get_subscriptions(device_info: DeviceInfo) -> list[Subscription]:
    return [
        # iot/atr/[command]]/[did]]/[class]]/[resource]/j
        Subscription(
            f"iot/atr/+/{device_info.did}/{device_info.get_class}/{device_info.resource}/j"
        ),
        # iot/p2p/[command]]/[sender did]/[sender class]]/[sender resource]
        # /[receiver did]/[receiver class]]/[receiver resource]/[q|p/[request id/j
        # [q|p] q-> request p-> response
        Subscription(
            f"iot/p2p/+/+/+/+/{device_info.did}/{device_info.get_class}/{device_info.resource}/q/+/j"
        ),
        Subscription(
            f"iot/p2p/+/{device_info.did}/{device_info.get_class}/{device_info.resource}/+/+/+/p/+/j"
        ),
    ]


def _default_ssl_context() -> ssl.SSLContext:
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    return ssl_ctx


@dataclass(frozen=True)
class MqttConnectionConfig:
    """Mqtt connection properties."""

    config: InitVar[Configuration]
    port: int = 443
    hostname: str = "mq.ecouser.net"
    ssl_context: ssl.SSLContext | bool = field(default_factory=_default_ssl_context)

    def __post_init__(self, config: Configuration) -> None:
        for _field in fields(self):
            # If there is a default and the value of the field is none we can assign a value
            if (
                not isinstance(_field.default, _MISSING_TYPE)
                and getattr(self, _field.name) is None
            ):
                object.__setattr__(self, _field.name, _field.default)

        if (
            self.hostname == MqttConnectionConfig.hostname
            and config.country.lower() != "cn"
        ):
            object.__setattr__(self, "hostname", f"mq-{config.continent}.ecouser.net")


class MqttClient:
    """MQTT client."""

    def __init__(
        self,
        config: Configuration,
        authenticator: Authenticator,
        connection_config: MqttConnectionConfig,
    ):
        self._config = config
        self._authenticator = authenticator
        self._subscribers: MutableMapping[str, SubscriberInfo] = {}
        self._connection_config = connection_config

        self._client: Client | None = None
        self._received_p2p_commands: MutableMapping[
            str, CommandHandlingMqttP2P
        ] = TTLCache(maxsize=60 * 60, ttl=60)
        self._last_message_received_at: datetime | None = None

        # pylint: disable=unused-argument
        async def __on_message(
            client: Client, topic: str, payload: bytes, qos: int, properties: dict
        ) -> None:
            _LOGGER.debug("Got message: topic=%s; payload=%s;", topic, payload.decode())
            self._last_message_received_at = datetime.now()

            topic_split = topic.split("/")
            if topic.startswith("iot/atr"):
                await self._handle_atr(topic_split, payload)
            elif topic.startswith("iot/p2p"):
                self._handle_p2p(topic_split, payload)
            else:
                _LOGGER.debug("Got unsupported topic: %s", topic)

        self._on_message = __on_message

        def on_credentials_changed(credentials: Credentials) -> None:
            if self._client:
                self._client.set_auth_credentials(
                    credentials.user_id, credentials.token
                )
                asyncio.create_task(self.reconnect())

        authenticator.subscribe(on_credentials_changed)

    @property
    def last_message_received_at(self) -> datetime | None:
        """Return the datetime of the last received message or None."""
        return self._last_message_received_at

    async def initialize(self) -> None:
        """Initialize MQTT."""
        if self._client:
            await self.reconnect()
            return

        credentials = await self._authenticator.authenticate()
        client_id = f"{credentials.user_id}@ecouser/{self._config.device_id}"
        self._client = Client(client_id)
        self._client.on_message = self._on_message
        self._client.set_auth_credentials(credentials.user_id, credentials.token)

        # pylint: disable=unused-argument
        def on_connect(client: Client, flags: int, code: int, properties: dict) -> None:
            if self._subscribers:
                _LOGGER.debug("Subscribe again to all previous subscriptions")
                for _, info in self._subscribers.items():
                    client.subscribe(info.subscriptions)

        self._client.on_connect = on_connect

        await self._client.connect(
            self._connection_config.hostname,
            self._connection_config.port,
            ssl=self._connection_config.ssl_context,
            version=MQTTv311,
        )

    def subscribe(self, vacuum_bot: VacuumBot) -> None:
        """Subscribe for messages for given vacuum."""
        if self._client is None:
            raise NotInitializedError

        device_info = vacuum_bot.device_info
        sub_info = self._subscribers.setdefault(
            device_info.did,
            SubscriberInfo(
                bot=vacuum_bot, subscriptions=_get_subscriptions(device_info)
            ),
        )

        self._client.subscribe(sub_info.subscriptions)

    def unsubscribe(self, vacuum_bot: VacuumBot) -> None:
        """Unsubscribe given vacuum."""
        device_info = vacuum_bot.device_info

        if self._subscribers.pop(device_info.did, None) and self._client:
            for subscription in _get_subscriptions(device_info):
                self._client.unsubscribe(subscription.topic)

    async def reconnect(self) -> None:
        """Reconnect."""
        if self._client:
            await self._client.reconnect()

    async def disconnect(self) -> None:
        """Disconnect from MQTT."""
        if self._client:
            await self._client.disconnect()
        self._subscribers.clear()

    async def _handle_atr(self, topic_split: list[str], payload: bytes) -> None:
        try:
            sub_info = self._subscribers.get(topic_split[3])
            if sub_info:
                data = json.loads(payload)
                await sub_info.bot.handle_message(topic_split[2], data)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.error(
                "An exception occurred during handling atr message", exc_info=True
            )

    def _handle_p2p(self, topic_split: list[str], payload: bytes) -> None:
        try:
            command_name = topic_split[2]
            command_type = COMMANDS_WITH_MQTT_P2P_HANDLING.get(command_name, None)
            if command_type is None:
                # command does not support p2p handling (yet)
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

                self._received_p2p_commands[request_id] = command_type(**data)
            else:
                command = self._received_p2p_commands.get(request_id, None)
                if not command:
                    _LOGGER.debug(
                        "Response to command came in probably to late. requestId=%s, commandName=%s",
                        request_id,
                        command_name,
                    )
                    return

                sub_info = self._subscribers.get(topic_split[3])
                if sub_info:
                    data = json.loads(payload)
                    command.handle_mqtt_p2p(sub_info.bot.events, data)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.error(
                "An exception occurred during handling p2p message", exc_info=True
            )


@dataclass(frozen=True)
class SubscriberInfo:
    """Subscriber information."""

    bot: VacuumBot
    subscriptions: list[Subscription]
