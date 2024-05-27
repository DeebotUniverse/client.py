from __future__ import annotations

from abc import ABC, abstractmethod
import contextlib
from dataclasses import dataclass, field
from datetime import datetime
import os
from pprint import pformat
import re
from time import sleep
from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple

import docker
from docker.errors import APIError, NotFound

if TYPE_CHECKING:
    from docker.client import DockerClient
    from docker.models.containers import Container

DOCKER_HOST_TCP_FORMAT = re.compile(r"^tcp://(\d+\.\d+\.\d+\.\d+)(?::\d+)?$")


class ContainerNotStartedError(Exception):
    """Container not started exception."""


@dataclass()
class ContainerConfiguration:
    """Container configuration."""

    image: str
    version: str = "latest"
    port: None | int = None
    env: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)
    max_wait_started: int = 30


class HostPort(NamedTuple):
    """Host port tuple."""

    host: str
    port: int


class BaseContainer(ABC):
    """Abstract base container."""

    docker_version = "auto"
    base_image_options: ClassVar[dict[str, Any]] = {
        "cap_add": ["IPC_LOCK"],
        "mem_limit": "1g",
        "environment": {},
        "detach": True,
        "publish_all_ports": True,
    }

    @property
    @abstractmethod
    def name(self) -> str:
        """Container name."""

    @property
    @abstractmethod
    def config(self) -> ContainerConfiguration:
        """Return container configuration."""

    @abstractmethod
    def check(self) -> bool:
        """Return True if container is started successfully."""

    def __init__(self) -> None:
        self.container: Container | None = None
        self._start_time: datetime = datetime(1970, 1, 1)

    @property
    def image(self) -> str:
        """Return used image."""
        return f"{self.config.image}:{self.config.version}"

    @property
    def host(self) -> str:
        """Return the host."""
        return self.get_host()

    def get_ports(self) -> dict[str, int]:
        """Get all service ports and their mapping."""
        if self.container is None:
            raise ContainerNotStartedError

        network = self.container.attrs["NetworkSettings"]
        result = {}
        for port, value in network["Ports"].items():
            if port == "6543/tcp":
                continue

            result[port] = int(value[0]["HostPort"])

        return result

    def get_port(self, port: None | str | int = None) -> int:
        """Get used port for the given port or main service port."""
        if port is None:
            port = self.config.port
        if port is None:
            port = next(iter(self.config.options["ports"]))
        if isinstance(port, int):
            port = f"{port}/tcp"

        assert isinstance(port, str)

        return self.get_ports()[port]

    def get_host(self) -> str:
        """Get host."""
        if self.container is None:
            raise ContainerNotStartedError

        host: str = self.container.attrs["NetworkSettings"]["IPAddress"]

        if host != "":
            if os.environ.get("TESTING", "") == "jenkins":
                pass

            # Support remote docker instance exposed via tcp
            # https://docs.docker.com/engine/reference/commandline/cli/
            elif DOCKER_HOST_TCP_FORMAT.match(os.environ.get("DOCKER_HOST", "")):
                if match := DOCKER_HOST_TCP_FORMAT.match(
                    os.environ.get("DOCKER_HOST", "")
                ):
                    host = match.group(1)
            else:
                host = "localhost"

        return host

    def get_image_options(self) -> dict[str, Any]:
        """Get all options."""
        image_options = self.base_image_options.copy()
        env: dict[str, Any] = image_options.setdefault("environment", {})

        for key, value in self.config.env.items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value

        image_options.update(self.config.options)
        return image_options

    def logs(self, *, since_last_start: bool = True) -> str:
        """Get docker container logs."""
        if self.container is None:
            raise ContainerNotStartedError

        if since_last_start:
            logs: bytes = self.container.logs(since=self._start_time)
        else:
            logs = self.container.logs()
        return logs.decode("utf-8")

    def run(self) -> HostPort:
        """Run container."""
        docker_client: DockerClient = docker.from_env(version=self.docker_version)
        image_options = self.get_image_options()

        # Create a new one
        self.container = docker_client.containers.run(image=self.image, **image_options)
        container_id = self.container.id
        count = 0

        self.container = docker_client.containers.get(container_id)

        started = False

        print(f"starting {self.name}")
        while count < self.config.max_wait_started and not started:
            if count > 0:
                sleep(1)
            count += 1

            try:
                self.container = docker_client.containers.get(container_id)
            except NotFound:
                print(f"Container not found for {self.name}")
                continue

            if self.container.status == "exited":
                logs = self.container.logs()
                self.stop()
                msg = f"Container failed to start {logs}"
                raise Exception(msg)

            if self.get_host() != "":
                started = self.check()

        if not started:
            logs = self.container.logs().decode("utf-8")
            self.stop()
            msg = (
                f"Could not start {self.name}: {logs}\n"
                f"Image: {self.image}\n"
                f"Options:\n{pformat(image_options)}"
            )
            raise Exception(msg)

        print(f"{self.name} started")
        self._start_time = datetime.now()

        return HostPort(self.get_host(), self.get_port())

    def stop(self) -> None:
        """Stop container."""
        if self.container is not None:
            with contextlib.suppress(APIError):
                self.container.kill()
            with contextlib.suppress(APIError):
                self.container.remove(v=True, force=True)
