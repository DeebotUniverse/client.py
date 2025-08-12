from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from types import ModuleType

    from _pytest.mark import ParameterSet


def load_data_folder(
    folder: str, extract_fn: Callable[[ModuleType, str], ParameterSet]
) -> Iterator[ParameterSet]:
    """Iterate over all files in tests/data/[folder] and call passed extract function."""
    map_data_dir = Path(__file__).parent / "data" / folder

    if not map_data_dir.exists():
        msg = f"Directory {map_data_dir} does not exist."
        raise FileNotFoundError(msg)

    for file in map_data_dir.iterdir():
        if file.suffix == ".py" and not file.name.startswith("__"):
            file_path = map_data_dir / file

            # Load the module dynamically
            filename = file.name[:-3]
            spec = importlib.util.spec_from_file_location(
                f"map_data_{filename}", file_path
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                yield extract_fn(module, filename)
