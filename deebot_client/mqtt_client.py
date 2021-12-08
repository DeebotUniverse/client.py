"""MQTT module."""
import json
import ssl
from typing import Dict, List, MutableMapping, Optional

from cachetools import TTLCache
from gmqtt import Client, Subscription
from gmqtt.mqtt.constants import MQTTv311

from .authentication import Authenticator
from .commands import COMMANDS_WITH_HANDLING, CommandWithHandling
from .logging_filter import get_logger
from .models import Configuration, Credentials, DeviceInfo
from .vacuum_bot import VacuumBot

_LOGGER = get_logger(__name__)


def _get_subscriptions(device_info: DeviceInfo) -> List[Subscription]:
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


class NotInitializedError(Exception):
    """Thrown when not class was not initialized correctly."""


class MqttClient:
    """MQTT client."""

    def __init__(self, config: Configuration, authenticator: Authenticator):
        self._config = config
        self._authenticator = authenticator
        self._subscribers: MutableMapping[str, VacuumBot] = {}
        self._port = 443
        self._hostname = f"mq-{config.continent}.ecouser.net"
        if config.country.lower() == "cn":
            self._hostname = "mq.ecouser.net"

        self._client: Optional[Client] = None
        self._received_commands: MutableMapping[str, CommandWithHandling] = TTLCache(
            maxsize=60 * 60, ttl=60
        )

        # pylint: disable=unused-argument
        async def _on_message(
            client: Client, topic: str, payload: bytes, qos: int, properties: Dict
        ) -> None:
            _LOGGER.debug("Got message: topic=%s; payload=%s;", topic, payload.decode())
            topic_split = topic.split("/")
            if topic.startswith("iot/atr"):
                await self._handle_atr(topic_split, payload)
            elif topic.startswith("iot/p2p"):
                self._handle_p2p(topic_split, payload)
            else:
                _LOGGER.debug("Got unsupported topic: %s", topic)

        self.__on_message = _on_message

        def on_credentials_changed(credentials: Credentials) -> None:
            if self._client:
                self._client.set_auth_credentials(
                    credentials.user_id, credentials.token
                )

        authenticator.subscribe(on_credentials_changed)

    async def initialize(self) -> None:
        """Initialize MQTT."""
        if self._client:
            self.disconnect()

        credentials = await self._authenticator.authenticate()
        client_id = f"{credentials.user_id}@ecouser/{self._config.device_id}"
        self._client = Client(client_id)
        self._client.on_message = self.__on_message
        self._client.set_auth_credentials(credentials.user_id, credentials.token)

        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        await self._client.connect(
            self._hostname, self._port, ssl=ssl_ctx, version=MQTTv311
        )

    async def subscribe(self, vacuum_bot: VacuumBot) -> None:
        """Subscribe for messages for given vacuum."""
        if self._client is None:
            raise NotInitializedError

        device_info = vacuum_bot.device_info
        self._client.subscribe(_get_subscriptions(device_info))
        self._subscribers[device_info.did] = vacuum_bot

    def unsubscribe(self, vacuum_bot: VacuumBot) -> None:
        """Unsubscribe given vacuum."""
        device_info = vacuum_bot.device_info

        if self._subscribers.pop(device_info.did, None) and self._client:
            for subscription in _get_subscriptions(device_info):
                self._client.unsubscribe(subscription.topic)

    def disconnect(self) -> None:
        """Disconnect from MQTT."""
        if self._client:
            self._client.disconnect()
        self._subscribers.clear()

    async def _handle_atr(self, topic_split: List[str], payload: bytes) -> None:
        try:
            bot = self._subscribers.get(topic_split[3])
            if bot:
                data = json.loads(payload)
                await bot.handle_message(topic_split[2], data)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.error(
                "An exception occurred during handling atr message", exc_info=True
            )

    def _handle_p2p(self, topic_split: List[str], payload: bytes) -> None:
        try:
            command_name = topic_split[2]
            command_type = COMMANDS_WITH_HANDLING.get(command_name, None)
            if command_type is None:
                # command is not supported yet
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

                self._received_commands[request_id] = command_type(**data)
            else:
                command = self._received_commands.get(request_id, None)
                if not command:
                    _LOGGER.debug(
                        "Response to command came in probably to late. requestId=%s, commandName=%s",
                        request_id,
                        command_name,
                    )
                    return

                bot = self._subscribers.get(topic_split[3])
                if bot:
                    data = json.loads(payload)
                    command.handle_mqtt_p2p(bot.events, data)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.error(
                "An exception occurred during handling p2p message", exc_info=True
            )
