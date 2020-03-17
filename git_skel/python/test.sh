#!/bin/bash -eux

# We use "python3" here so we can use the virtualenv's Python interpreter and libraries
python3 -m mypy *.py tests/*.py
python3 -m pytest
python3 -m yapf -ipr *.py tests/*.py
python3 -m pylint *.py
