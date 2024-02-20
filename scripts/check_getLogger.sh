#!/usr/bin/env bash
set -eu

# Dummy script to check if getLogger is somewhere called except in logging_filter.py

# List of keywords to search for
KEYWORDS="getLogger\|logging"

# Find all Python files under deebot_client/ except logging_filter.py
# For each file, search for the keywords using grep
# If any match is found, print a message indicating that getLogger is used incorrectly
# Exit with an error code if any match is found
find deebot_client/ -name "*.py" \
  ! -name "logging_filter.py" \
  -exec grep -qi -w "$KEYWORDS" {} \; \
  -exec echo "{} uses the logger incorrectly. Use 'deebot_client.logging_filter.get_logger' instead." \; \
  -exec false {} +
exit
