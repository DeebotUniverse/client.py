"""Remove PyO3 macro attribute lines from an lcov coverage report.

PyO3 generated wrappers (e.g. for getters or methods without arguments) only
have a coverage counter on the error path. Their lines are therefore reported
as uncovered even if they are called. See https://github.com/PyO3/pyo3/issues/6545
The method bodies have their own counters, so no real coverage information is lost.
"""

from __future__ import annotations

import argparse
from functools import cache
from pathlib import Path
import re

_PYO3_MACRO = re.compile(r"^\s*#\[py(methods|class)\b")


@cache
def _source_lines(path: str) -> list[str]:
    return Path(path).read_text(encoding="utf-8").splitlines()


def filter_lcov(content: str) -> tuple[str, int]:
    """Filter PyO3 macro lines from lcov content.

    Return the filtered content and the number of removed lines.
    """
    output: list[str] = []
    source: str | None = None
    hit = found = removed = 0

    for line in content.splitlines(keepends=True):
        if line.startswith("SF:"):
            source = line[3:].strip()
            hit = found = 0
        elif line.startswith("DA:") and source:
            line_no, count = line[3:].split(",")[:2]
            lines = _source_lines(source)
            index = int(line_no) - 1
            if index < len(lines) and _PYO3_MACRO.match(lines[index]):
                removed += 1
                continue
            found += 1
            if int(count) > 0:
                hit += 1
        elif line.startswith("LF:"):
            output.append(f"LF:{found}\n")
            continue
        elif line.startswith("LH:"):
            output.append(f"LH:{hit}\n")
            continue
        output.append(line)

    return "".join(output), removed


def main() -> None:
    """Run the script."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", type=Path, help="lcov file to filter")
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        help="output file (default: overwrite input)",
    )
    args = parser.parse_args()

    content, removed = filter_lcov(args.input.read_text(encoding="utf-8"))
    (args.output or args.input).write_text(content, encoding="utf-8")
    print(f"Removed {removed} PyO3 macro lines from {args.input}")  # noqa: T201


if __name__ == "__main__":
    main()
