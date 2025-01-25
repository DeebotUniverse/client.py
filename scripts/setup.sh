#!/usr/bin/env bash
set -eu

# Setup development environment

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install required packages for rust-lzma
sudo apt update

# Install project dependencies
uv sync --frozen --group dev

# Setup maturin development hook
python -m maturin_import_hook site install --uv

# Setup pre-commit
pre-commit install