#!/usr/bin/env bash
set -eu

# Setup development environment

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install required packages for rust-lzma
sudo apt update

# Install project dependencies
uv sync --frozen --group dev

# Setup pre-commit
pre-commit install