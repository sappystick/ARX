#!/bin/sh
set -e
make setup
make verify-quick
python3 tests/regress.py
