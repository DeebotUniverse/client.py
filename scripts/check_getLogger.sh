#!/bin/bash
# Dummy script to check if getLogger is somewhere called execpt in logging.py

# LIST='list\|of\|words\|split\|by\|slash\|and\|pipe'
LIST="getLogger"

for FILE in `find deebot_client/ -name "*.py"` ; do
    # Check if the file contains one of the words in LIST
    if [[ $FILE = "deebot_client/logging.py" ]]; then
      continue;
    fi

    if grep -w $LIST $FILE; then
      echo $FILE " has one of the word you don't want to commit. Please remove it"
      exit 1
    fi
      done
exit