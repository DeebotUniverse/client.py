"""MQTT module."""
import asyncio
import json
import ssl
from collections.abc import Callable, MutableMapping
from dataclasses import _MISSING_TYPE, InitVar, dataclass, field, fields
from datetime import datetime

from asyncio_mqtt import Client, Message, MqttError
from cachetools import TTLCache

from deebot_client.events.event_bus import EventBus

from .authentication import Authenticator
from .commands import COMMANDS_WITH_MQTT_P2P_HANDLING, CommandHandlingMqttP2P
from .logging_filter import get_logger
from .models import Configuration, Credentials, DeviceInfo

RECONNECT_INTERVAL = 5  # seconds

_LOGGER = get_logger(__name__)


def _get_topics(device_info: DeviceInfo) -> list[str]:
    return [
        # iot/atr/[command]]/[did]]/[class]]/[resource]/j
        f"iot/atr/+/{device_info.did}/{device_info.get_class}/{device_info.resource}/j",
        # iot/p2p/[command]]/[sender did]/[sender class]]/[sender resource]
        # /[receiver did]/[receiver class]]/[receiver resource]/[q|p]/[request id]/j
        # [q|p] q-> request p-> response
        f"iot/p2p/+/+/+/+/{device_info.did}/{device_info.get_class}/{device_info.resource}/q/+/j",
        f"iot/p2p/+/{device_info.did}/{device_info.get_class}/{device_info.resource}/+/+/+/p/+/j",
    ]


def _default_ssl_context() -> ssl.SSLContext:
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    return ssl_ctx


@dataclass(frozen=True)
class MqttConfiguration:
    """Mqtt configuration."""

    config: InitVar[Configuration]
    port: int = 443
    hostname: str = "mq.ecouser.net"
    ssl_context: ssl.SSLContext | None = field(default_factory=_default_ssl_context)
    device_id: str = field(init=False)

    def __post_init__(self, config: Configuration) -> None:
        for _field in fields(self):
            # If there is a default and the value of the field is none we can assign a value
            if (
                not isinstance(_field.default, _MISSING_TYPE)
                and getattr(self, _field.name) is None
            ):
                object.__setattr__(self, _field.name, _field.default)

        object.__setattr__(self, "device_id", config.device_id)

        if (
            self.hostname == MqttConfiguration.hostname
            and config.country.lower() != "cn"
        ):
            object.__setattr__(self, "hostname", f"mq-{config.continent}.ecouser.net")


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
    ):
        self._config = config
        self._authenticator = authenticator

        self._subscribtions: MutableMapping[str, SubscriberInfo] = {}
        self._subscribtion_changes: asyncio.Queue[
            tuple[SubscriberInfo | DeviceInfo, bool]
        ] = asyncio.Queue()
        self._mqtt_task: asyncio.Task | None = None

        self._received_p2p_commands: MutableMapping[
            str, CommandHandlingMqttP2P
        ] = TTLCache(maxsize=60 * 60, ttl=60)
        self._last_message_received_at: datetime | None = None

        def on_credentials_changed(_: Credentials) -> None:
            asyncio.create_task(self._create_mqtt_task())

        authenticator.subscribe(on_credentials_changed)
        asyncio.create_task(self._create_mqtt_task())

    @property
    def last_message_received_at(self) -> datetime | None:
        """Return the datetime of the last received message or None."""
        return self._last_message_received_at

    async def _get_client(self) -> Client:
        credentials = await self._authenticator.authenticate()
        client_id = f"{credentials.user_id}@ecouser/{self._config.device_id}"
        return Client(
            hostname=self._config.hostname,
            port=self._config.port,
            username=credentials.user_id,
            password=credentials.token,
            client_id=client_id,
            tls_context=self._config.ssl_context,
        )

    async def _cancel_mqtt_task(self) -> None:
        if self._mqtt_task is not None and self._mqtt_task.cancel():
            # Wait for the task to be cancelled
            try:
                await self._mqtt_task
            except asyncio.CancelledError:
                pass

    async def _create_mqtt_task(self) -> None:
        async def mqtt() -> None:
            while True:
                try:
                    async with (await self._get_client()) as client:
                        _LOGGER.debug("Subscribe to all previous subscriptions")
                        for _, info in self._subscribtions.items():
                            for topic in _get_topics(info.device_info):
                                await client.subscribe(topic)

                        async def listen() -> None:
                            async with client.messages() as messages:
                                async for message in messages:
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

                except MqttError:
                    _LOGGER.warning(
                        "Connection lost; Reconnecting in %d seconds ...",
                        RECONNECT_INTERVAL,
                        exc_info=True,
                    )
                    await asyncio.sleep(RECONNECT_INTERVAL)
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.error("An exception occurred", exc_info=True)

        await self._cancel_mqtt_task()
        self._mqtt_task = asyncio.create_task(mqtt())

    def _handle_message(self, message: Message) -> None:
        _LOGGER.debug(
            "Got message: topic=%s, payload=%s", message.topic, message.payload
        )
        self._last_message_received_at = datetime.now()

        if message.payload is None or isinstance(message.payload, (int, float)):
            _LOGGER.warning(
                "Unexpected message: tpoic=%s, payload=%s",
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
            (info, add) = await self._subscribtion_changes.get()

            if isinstance(info, SubscriberInfo):
                device_info = info.device_info
            else:
                device_info = info
                add = False

            for topic in _get_topics(device_info):
                if add:
                    await client.subscribe(topic)
                else:
                    await client.unsubscribe(topic)

            if add and isinstance(info, SubscriberInfo):
                self._subscribtions[device_info.did] = info
            else:
                self._subscribtions.pop(device_info.did, None)

            self._subscribtion_changes.task_done()

    async def subscribe(self, info: SubscriberInfo) -> None:
        """Subscribe for messages from given vacuum."""
        await self.connect()
        self._subscribtion_changes.put_nowait((info, True))

    def unsubscribe(self, device_info: DeviceInfo) -> None:
        """Unsubscribe given vacuum."""
        self._subscribtion_changes.put_nowait((device_info, False))

    async def connect(self) -> None:
        """Connect to MQTT."""
        if self._mqtt_task is None or self._mqtt_task.done():
            await self._create_mqtt_task()

    async def disconnect(self) -> None:
        """Disconnect from MQTT."""
        await self._cancel_mqtt_task()

    def _handle_atr(
        self, topic_split: list[str], payload: str | bytes | bytearray
    ) -> None:
        try:
            sub_info = self._subscribtions.get(topic_split[3])
            if sub_info:
                sub_info.callback(topic_split[2], payload)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.error(
                "An exception occurred during handling atr message", exc_info=True
            )

    def _handle_p2p(
        self, topic_split: list[str], payload: str | bytes | bytearray
    ) -> None:
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

                sub_info = self._subscribtions.get(topic_split[3])
                if sub_info:
                    data = json.loads(payload)
                    command.handle_mqtt_p2p(sub_info.events, data)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.error(
                "An exception occurred during handling p2p message", exc_info=True
            )
