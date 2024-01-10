from deebot_client.commands.xml import GetError
from deebot_client.events import ErrorEvent
from tests.helpers import get_request_xml

from . import assert_command


async def test_getErrors() -> None:
    json = get_request_xml("<ctl ret='ok' errs=''/>")
    await assert_command(
        GetError(), json, ErrorEvent(0, "NoError: Robot is operational")
    )
