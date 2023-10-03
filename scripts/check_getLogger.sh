#!/bin/bash
# Dummy script to check if getLogger is somewhere called except in logging_filter.py

# LIST='list\|of\|words\|split\|by\|slash\|and\|pipe'
LIST="getLogger\|logging"

for FILE in `find deebot_client/ -name "*.py"` ; do
    # Check if the file contains one of the words in LIST
    if [[ $FILE = "deebot_client/logging_filter.py" ]]; then
      continue;
    fi

    if grep -i -w $LIST $FILE; then
      echo $FILE " uses not the logger provided from deebot_client.logging_filter.get_logger. You need to use them"
      exit 1
    fi
      done
exit