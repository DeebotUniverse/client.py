from deebot_client.commands import GetError
from deebot_client.events import ErrorEvent
from tests.commands import assert_command
from tests.helpers import get_request_xml


async def test_getErrorsXml() -> None:
    json = get_request_xml("<ctl ret='ok' errs=''/>")
    await assert_command(GetError(), json, ErrorEvent(0, "NoError: Robot is operational"))
