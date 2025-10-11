"""Script to check for similar models and link them to the same hardware implementation."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
import time

import aiohttp
import orjson

from deebot_client.api_client import ApiClient
from deebot_client.authentication import Authenticator, create_rest_config
from deebot_client.hardware import DEVICES, _load
from deebot_client.util import md5


def _save_file(name: str, data: dict[str, list[str]]) -> None:
    """Save data to file."""
    path = Path("similarity_output")
    path.mkdir(exist_ok=True)
    with path.joinpath(name).open("w") as f:
        f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2).decode("utf-8"))


def _add_models_by_similarity(models: list[str]) -> None:
    """Add models by similarity."""
    if len(models) < 2:
        # No similar models
        return

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
                    dir_fd=os.open("deebot_client/hardware", os.O_RDONLY),
                )


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

        iot_map = await api_client.get_product_iot_map()
        name_map: dict[str, list[str]] = {}
        ui_logic_map: dict[str, list[str]] = {}
        for key, value in iot_map.items():
            name_map.setdefault(value["name"], []).append(key)
            ui_logic_map.setdefault(value["UILogicId"], []).append(key)

        await asyncio.get_event_loop().run_in_executor(
            None, _save_file, "models_map.json", name_map
        )
        await asyncio.get_event_loop().run_in_executor(
            None, _save_file, "ui_logic_map.json", ui_logic_map
        )

        # Load current models
        await asyncio.get_event_loop().run_in_executor(None, _load)

        for map_obj in (name_map, ui_logic_map):
            for models in map_obj.values():
                _add_models_by_similarity(models)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
