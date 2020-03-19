#!/usr/bin/env bash

if [[ -z "${VIRTUAL_ENV}" ]]; then
    virtualenv -p python3 venv
fi

source ./venv/bin/activate

pip install -r pip-requirements.txt

# Clean build
# pip install --force-reinstall --no-cache-dir --no-binary :all: -r requirements.txt

rm -rf ./build ./dist ./bundle

pyinstaller --onefile ./evdevremapkeys/evdevremapkeys.py

mkdir bundle

staticx ./dist/evdevremapkeys ./bundle/evdevremapkeys