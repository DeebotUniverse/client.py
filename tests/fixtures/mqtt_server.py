# Copyright (c) 2020-2022 Andreas Motl <andreas.motl@panodata.org>
# Copyright (c) 2020-2022 Richard Pobering <richard.pobering@panodata.org>
#
# Use of this source code is governed by an MIT-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.

"""
Provide the `Mosquitto`_ MQTT broker as a session-scoped fixture to your test harness.

Source: https://github.com/hiveeyes/terkin-datalogger/blob/0.13.0/test/fixtures/mosquitto.py

.. _Mosquitto: https://github.com/eclipse/mosquitto
"""
from datetime import datetime
from typing import Any

import docker
from pytest_docker_fixtures import images
from pytest_docker_fixtures.containers._base import BaseImage

images.settings["mosquitto"] = {
    "image": "eclipse-mosquitto",
    "version": "2.0.15",
    "options": {
        "command": "mosquitto -c /mosquitto-no-auth.conf",
        "publish_all_ports": False,
        "ports": {"1883/tcp": "1883"},
        "privileged": False,
    },
}


class MqttServer(BaseImage):  # type: ignore[misc]
    """Mqtt test server."""

    name = "mosquitto"
    port = 1883

    def __init__(self) -> None:
        super().__init__()
        self._start_time: datetime = datetime(1, 1, 1)

    def logs(self, since_last_start: bool = True) -> str:
        """Get docker container logs."""
        if since_last_start:
            logs: bytes = self.container_obj.logs(since=self._start_time)
        else:
            logs = self.container_obj.logs()
        return logs.decode("utf-8")

    def check(self) -> bool:
        """Check if container is started."""
        return (
            f"mosquitto version {images.settings[self.name]['version']} running"
            in self.logs()
        )

    def pull_image(self) -> None:
        """
        Image needs to be pull explicitly.

        Workaround against `404 Client Error: Not Found for url: http+docker://localhost/v1.23/containers/create`.

        - https://github.com/jpmens/mqttwarn/pull/589#issuecomment-1249680740
        - https://github.com/docker/docker-py/issues/2101
        """
        docker_client = docker.from_env(version=self.docker_version)
        image_name = self.image
        if not docker_client.images.list(name=image_name):
            docker_client.images.pull(image_name)

    def run(self) -> tuple[str | Any, str | None]:
        """Run container."""
        self.pull_image()
        self._start_time = datetime.now()
        return super().run()  # type: ignore[no-any-return]
