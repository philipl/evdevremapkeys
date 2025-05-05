#!/usr/bin/env bash
# Builds a single binary executable version of evdevremapkeys

rm -rf ./build ./dist ./bundle

uv run pyinstaller --onefile ./evdevremapkeys/evdevremapkeys.py

mkdir bundle

uv run staticx ./dist/evdevremapkeys ./bundle/evdevremapkeys
