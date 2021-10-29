"""Base command."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union


class Command(ABC):
    """Abstract command object."""

    def __init__(self, args: Union[Dict, List, None] = None) -> None:
        if args is None:
            args = {}
        self._args = args

    @classmethod
    @property
    @abstractmethod
    def name(cls) -> str:
        """Command name."""
        raise NotImplementedError

    @property
    def args(self) -> Union[Dict[str, Any], List]:
        """Command additional arguments."""
        return self._args
