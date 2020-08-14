#!/usr/bin/env bash
# Builds a single binary executable version of evdevremapkeys

rm -rf ./build ./dist ./bundle

if [[ -z "${VIRTUAL_ENV}" ]]; then
    virtualenv -p python3 venv
fi

source ./venv/bin/activate

pip install .
pip install -e '.[binary]'

# Clean build
# pip install --force-reinstall --no-cache-dir --no-binary :all: -r requirements.txt

pyinstaller --onefile ./evdevremapkeys/evdevremapkeys.py

mkdir bundle

staticx ./dist/evdevremapkeys ./bundle/evdevremapkeys