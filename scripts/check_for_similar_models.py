"""Script to check for similar models and link them to the same hardware implementation."""

from __future__ import annotations

import asyncio
import logging
import os
import time

import aiohttp

from deebot_client.api_client import ApiClient
from deebot_client.authentication import Authenticator, create_rest_config
from deebot_client.hardware.deebot import DEVICES, _load
from deebot_client.util import md5


async def main() -> None:
    """Execute script."""
    async with aiohttp.ClientSession() as session:
        logging.basicConfig(level=logging.DEBUG)
        rest = create_rest_config(
            session=session,
            device_id=md5(str(time.time())),
            alpha_2_country=os.environ["ECOVACS_COUNTRY"],
        )

        authenticator = Authenticator(
            rest, os.environ["ECOVACS_USERNAME"], md5(os.environ["ECOVACS_PASSWORD"])
        )
        api_client = ApiClient(authenticator)

        name_map: dict[str, list[str]] = {}
        for key, value in (await api_client.get_product_iot_map()).items():
            name_map.setdefault(value["name"], []).append(key)

        # Load current models
        await asyncio.get_event_loop().run_in_executor(None, _load)

        for models in name_map.values():
            if len(models) < 2:
                # No similar models
                continue

            model_to_link = None
            for model in models:
                if model in DEVICES:
                    model_to_link = model
                    break

            if model_to_link:
                # Found a model to link
                for model in models:
                    if model != model_to_link and model not in DEVICES:
                        os.symlink(
                            f"{model_to_link}.py",
                            f"{model}.py",
                            dir_fd=os.open(
                                "deebot_client/hardware/deebot", os.O_RDONLY
                            ),
                        )


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
