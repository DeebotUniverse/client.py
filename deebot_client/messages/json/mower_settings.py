"""Mower setting push messages."""

from __future__ import annotations

from deebot_client.commands.json.animal_protection import GetAnimalProtection
from deebot_client.commands.json.humanoid_ai import GetHumanoidAi
from deebot_client.commands.json.moveup_warning import GetMoveUpWarning
from deebot_client.commands.json.narrow_adapt import GetNarrowAdapt
from deebot_client.commands.json.recognization import GetRecognization
from deebot_client.commands.json.volume import GetVolume


class OnRecognization(GetRecognization):
    """AI recognition update."""

    NAME = "onRecognization"


class OnHumanoidAi(GetHumanoidAi):
    """Smart mowing with avoidance update."""

    NAME = "onHumanoidAI"


class OnNarrowAdapt(GetNarrowAdapt):
    """Narrow passage adaptation update."""

    NAME = "onNarrowAdapt"


class OnMoveUpWarning(GetMoveUpWarning):
    """Mower lifted alarm update."""

    NAME = "onMoveupWarning"


class OnAnimalProtection(GetAnimalProtection):
    """Animal protection configuration update."""

    NAME = "onAnimProtect"


class OnVolume(GetVolume):
    """Mower volume configuration update."""

    NAME = "onVolume"
