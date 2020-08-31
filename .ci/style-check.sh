#!/usr/bin/env bash

set -e
set -x

black --version
black --check .

flake8
