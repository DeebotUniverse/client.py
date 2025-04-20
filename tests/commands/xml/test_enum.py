from __future__ import annotations

import pytest

from deebot_client.commands.xml.enum import XmlStopReason
from deebot_client.events import CleanJobStatus


@pytest.mark.parametrize("enum_value", list(XmlStopReason))
def test_XmlStopReason_should_convert_to_CleanJobStatus(
    enum_value: XmlStopReason,
) -> None:
    converted = enum_value.clean_job_status
    assert converted is not None
    assert isinstance(converted, CleanJobStatus)
