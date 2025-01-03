#!/usr/bin/env bash
set -eu

# Setup development environment

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install required packages for rust-lzma
sudo apt update
sudo apt install -y pkg-config liblzma-dev

# Install project dependencies
uv sync --frozen --dev

# Setup pre-commit
pre-commit install