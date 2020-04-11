#!/usr/bin/env sh
# Copyright 2019 Wirepas Ltd

rm -f -r dist/
rm -f -r build/
py3clean . || true
python3 setup.py clean --all || true
python3 setup.py --version
python3 setup.py sdist bdist_wheel || true
