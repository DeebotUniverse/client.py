import asyncio

from deebot_client.event_bus import EventBus


async def block_till_done(event_bus: EventBus) -> None:
    """Block till done."""
    await asyncio.gather(*event_bus._tasks)
