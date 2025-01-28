#!/usr/bin/env sh
set -euxo pipefail

cd /github/workspace

# Remove sources otherwise pytest will complain about missing rust files
rm -rf deebot_client

uv pip install --no-progress --system --force-reinstall dist/deebot_client-*.whl
# Disable tests, which require docker for now
site-packages=$(python -c "import site; print(site.getsitepackages()[0])")
echo "site-packages: ${site-packages}"
pytest tests --cov=${site-packages}/deebot_client --cov-report=xml --junitxml=junit.xml -o junit_family=legacy -v -m "not docker"