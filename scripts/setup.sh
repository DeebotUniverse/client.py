#!/usr/bin/env bash
set -euxo pipefail

# Setup development environment

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync --frozen --group dev

# Setup maturin development hook
python -m maturin_import_hook site install

# Setup pre-commit
pre-commit install