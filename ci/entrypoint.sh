#!/usr/bin/env sh
set -euxo pipefail

cd /github/workspace

# Remove sources otherwise pytest will complain about missing rust files
rm -rf deebot_client

uv pip install --no-progress --system --force-reinstall dist/deebot_client-*.whl
# Disable tests, which require docker for now
pytest tests --cov=./ --cov-report=xml --junitxml=junit.xml -o junit_family=legacy -v -m "not docker"