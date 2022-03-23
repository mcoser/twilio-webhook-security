#!/bin/bash -x
PWD=`pwd`
echo $PWD

activate () {
    . $PWD/venv/bin/activate
}

FILE=./venv/
if test -d "$FILE"; then
    echo "$FILE exists."
    activate
    python3 app.py
else
    /usr/local/bin/virtualenv --python=python3 venv
    activate
    pip install -r requirements.txt
    python3 app.py
fi
