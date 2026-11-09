"""KVS camera MQTT P2P listener for Ecovacs robots.

Ecovacs camera-equipped robots use a **dedicated JMQ MQTT broker** for all
camera-related P2P signaling.  This broker is separate from the standard
deebot-client broker (``mq-*.ecouser.net``) and is the only broker that
authorises the P2P camera topics — publishing to the regular broker on those
topics returns MQTT return-code 135 (Not Authorized), and the SUBSCRIBE
is silently dropped.

The JMQ broker hostname is continent-scoped:
``jmq-ngiot-{eu|na|as}.dc.ww.ecouser.net:443``

**P2P protocol**

The robot sends ``p2pReq`` messages to the viewer on topics matching::

    iot/p2p/{cmd}/{robot_did}/{robot_mid}/{robot_res}/{user_id}/ecouser/{user_res}/q/{req_id}/j

The viewer is expected to respond with a ``p2pDataResp`` on the corresponding
``/p/`` (response) topic so that the robot knows the request was received.

The commands of interest are:

- ``videoOpened`` — the robot acknowledges that it has opened its encoder and
  the video stream is ready.
- ``setAudioCallState`` — state-change notification (viewer connected /
  disconnected).
- ``p2pDataResp`` — generic P2P acknowledgement.

**Usage**

Create a single ``KvsMqttListener`` instance per HA installation (not per
robot), start it with ``await listener.start()``, and pass a ``on_p2p_req``
callback that dispatches messages to the correct robot handler by DID.

Outgoing messages (``videoOpened``, ``setAudioCallState``) should be queued
via ``enqueue_publish``; the listener drains the queue on the same persistent
connection used for subscriptions.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import contextlib
import datetime as _dt
import ssl
import time
from typing import Any

import aiomqtt
import orjson
from deebot_client.authentication import Authenticator
from deebot_client.logging_filter import get_logger

_LOGGER = get_logger(__name__)

_JMQ_BROKER_PORT = 443
_RECONNECT_DELAY = 5  # seconds between MQTT reconnection attempts
_MQTT_TIMEOUT = 30  # seconds for MQTT client keep-alive / connect timeout
_MQTT_QOS = 1  # QoS level for P2P subscriptions


def _jmq_host(continent: str) -> str:
    """Return the JMQ broker hostname for the given continent code (eu/na/as)."""
    region = continent if continent in ("eu", "na", "as") else "eu"
    return f"jmq-ngiot-{region}.dc.ww.ecouser.net"


class KvsMqttListener:
    """Persistent MQTT connection to the Ecovacs JMQ broker for KVS P2P signaling.

    A single TCP/TLS connection is used for both SUBSCRIBE (receiving robot
    P2P requests) and PUBLISH (sending viewer commands back to the robot).
    Outgoing messages are enqueued and drained by a background worker task on
    the same connection.

    The listener automatically reconnects after disconnections and refreshes
    the authentication token on each reconnect when an :class:`Authenticator`
    is provided.
    """

    def __init__(
        self,
        *,
        user_id: str,
        user_resource: str,
        on_p2p_req: Callable[[str, dict[str, Any]], None],
        authenticator: Authenticator | None = None,
        token: str | None = None,
        continent: str = "eu",
    ) -> None:
        """Initialize the KVS MQTT listener.

        Args:
            user_id: The Ecovacs account user ID.
            user_resource: The MQTT client resource string for this installation.
            on_p2p_req: Callback invoked for every incoming robot P2P request.
                Receives ``(topic: str, payload: dict)`` and must not block.
            authenticator: Preferred; enables automatic token refresh on
                reconnect.  Mutually exclusive with ``token``.
            token: Static auth token.  Use when no :class:`Authenticator` is
                available.  Not refreshed automatically.
            continent: Two-letter continent code (``eu``, ``na``, ``as``).
                Defaults to ``"eu"``.
        """
        if authenticator is None and token is None:
            msg = "Either 'authenticator' or 'token' must be provided"
            raise ValueError(msg)
        self._authenticator = authenticator
        self._token = token
        self._user_id = user_id
        self._user_resource = user_resource
        self._on_p2p_req = on_p2p_req
        self._continent = continent
        self._publish_queue: asyncio.Queue[tuple[str, bytes, int]] = asyncio.Queue()
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def _resolve_token(self) -> str:
        """Return a valid auth token, refreshing via Authenticator if available."""
        if self._authenticator is not None:
            creds = await self._authenticator.authenticate()
            return creds.token
        assert self._token is not None  # noqa: S101
        return self._token

    async def start(self) -> None:
        """Start the MQTT listener task (auto-reconnects on disconnect)."""
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_forever())

    async def stop(self) -> None:
        """Stop the MQTT listener task and wait for it to finish."""
        self._stop_event.set()
        if self._task is not None and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(TimeoutError, asyncio.CancelledError):
                await asyncio.wait_for(asyncio.shield(self._task), timeout=3.0)
        self._task = None

    async def enqueue_publish(self, topic: str, payload: bytes, qos: int = 0) -> None:
        """Enqueue a message for publish on the persistent MQTT connection.

        Thread-safe; can be called from any asyncio coroutine.
        """
        await self._publish_queue.put((topic, payload, qos))

    async def _run_forever(self) -> None:
        """Run the MQTT connection loop, reconnecting after each disconnection."""
        while not self._stop_event.is_set():
            try:
                await self._run()
            except asyncio.CancelledError:
                return
            except Exception as err:  # noqa: BLE001
                if not self._stop_event.is_set():
                    _LOGGER.warning("KVS MQTT error: %s", err)
            if not self._stop_event.is_set():
                _LOGGER.info(
                    "KVS MQTT disconnected — reconnecting in %ds", _RECONNECT_DELAY
                )
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(
                        self._stop_event.wait(), timeout=_RECONNECT_DELAY
                    )

    async def _run(self) -> None:
        """Establish a single MQTT connection, subscribe and dispatch messages."""
        loop = asyncio.get_running_loop()
        ssl_ctx = await loop.run_in_executor(None, ssl.create_default_context)
        # The Ecovacs JMQ video-signaling broker presents a certificate issued by
        # a private CA that is not in the system trust store, causing TLS
        # verification to fail with the default context.  Certificate verification
        # is therefore disabled for this specific connection only; the broker
        # hostname is a hard-coded Ecovacs infrastructure endpoint and the traffic
        # is additionally protected by MQTT credentials.
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        client_id = f"{self._user_id}@ecouser/{self._user_resource}"
        sub_topic = (
            f"iot/p2p/+/+/+/+/{self._user_id}/ecouser/{self._user_resource}/+/+/+"
        )

        _LOGGER.debug(
            "KVS MQTT: connecting to %s:%d client_id=%s",
            _jmq_host(self._continent),
            _JMQ_BROKER_PORT,
            client_id,
        )

        token = await self._resolve_token()
        publish_task: asyncio.Task[None] | None = None
        try:
            async with aiomqtt.Client(
                hostname=_jmq_host(self._continent),
                port=_JMQ_BROKER_PORT,
                username=self._user_id,
                password=token,
                identifier=client_id,
                tls_context=ssl_ctx,
                timeout=_MQTT_TIMEOUT,
            ) as client:
                _LOGGER.debug("KVS MQTT: connected, subscribing to %s", sub_topic)
                await client.subscribe(sub_topic, qos=_MQTT_QOS)
                publish_task = asyncio.create_task(
                    self._publish_worker(client, self._publish_queue)
                )

                async for message in client.messages:
                    if self._stop_event.is_set():
                        break
                    topic = str(message.topic)
                    try:
                        payload = orjson.loads(message.payload)
                    except orjson.JSONDecodeError:
                        raw = (
                            message.payload.decode(errors="replace")
                            if isinstance(message.payload, (bytes, bytearray))
                            else str(message.payload)
                        )
                        payload = {"raw": raw}

                    parts = topic.split("/")
                    if len(parts) >= 10 and parts[9] == "q":  # noqa: PLR2004
                        try:
                            self._on_p2p_req(topic, payload)
                        except Exception as err:  # noqa: BLE001
                            _LOGGER.warning("KVS MQTT on_p2p_req error: %s", err)

        finally:
            if publish_task is not None and not publish_task.done():
                publish_task.cancel()
                with contextlib.suppress(TimeoutError, asyncio.CancelledError):
                    await asyncio.wait_for(asyncio.shield(publish_task), timeout=2.0)

    @staticmethod
    async def _publish_worker(
        client: Any,
        queue: asyncio.Queue[tuple[str, bytes, int]],
    ) -> None:
        """Drain the publish queue and publish each message on ``client``."""
        while True:
            topic, payload, qos = await queue.get()
            try:
                await client.publish(topic, payload=payload, qos=qos)
                _LOGGER.debug("KVS MQTT publish OK: %s", topic[:80])
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("KVS MQTT publish error: %s | topic=%s", err, topic)
            finally:
                queue.task_done()

    async def send_p2p_data_resp(
        self,
        req_topic: str,
    ) -> None:
        """Acknowledge a robot P2P request with a ``p2pDataResp`` response.

        Parses the request topic to reconstruct the symmetric response topic
        (``/q/`` → ``/p/``) and sends a success acknowledgement so the robot
        knows the request was received and processed.

        Args:
            req_topic: The full topic string of the received P2P request.
        """
        parts = req_topic.split("/")
        if len(parts) < 12:  # noqa: PLR2004
            _LOGGER.warning("P2pDataResp: malformed request topic: %s", req_topic)
            return

        cmd = parts[2]
        app_user_id = parts[6]
        app_vendor = parts[7]
        app_res = parts[8]
        from_id = parts[3]
        from_class = parts[4]
        from_res = parts[5]
        req_id = parts[10]
        fmt = parts[11]

        resp_topic = (
            f"iot/p2p/{cmd}/{app_user_id}/{app_vendor}/{app_res}"
            f"/{from_id}/{from_class}/{from_res}/p/{req_id}/{fmt}"
        )

        ts = str(int(time.time() * 1000))
        tz_offset = int(
            (
                _dt.datetime.now(_dt.UTC).astimezone().utcoffset() or _dt.timedelta()
            ).total_seconds()
            / 60
        )
        resp_payload = orjson.dumps(
            {
                "header": {"pri": 1, "ts": ts, "tzm": tz_offset, "ver": "0.0.22"},
                "body": {"code": 0, "msg": "ok"},
            }
        )

        _LOGGER.debug("KVS MQTT p2pDataResp → %s", resp_topic)
        await self.enqueue_publish(resp_topic, resp_payload, qos=1)
