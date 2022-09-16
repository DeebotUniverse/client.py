"""Base command."""
from abc import ABC, abstractmethod
from typing import Any


class Command(ABC):
    """Abstract command object."""

    def __init__(self, args: dict | list | None = None) -> None:
        if args is None:
            args = {}
        self._args = args

    @classmethod
    @property
    @abstractmethod
    def name(cls) -> str:
        """Command name."""

    @property
    def args(self) -> dict[str, Any] | list:
        """Command additional arguments."""
        return self._args

    def __eq__(self, obj: object) -> bool:
        if isinstance(obj, Command):
            return self.name == obj.name and self.args == obj.args

        return False

    def __hash__(self) -> int:
        return hash(self.name) + hash(self.args)
