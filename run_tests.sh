#!/bin/bash
set -e

flake8 unicore --exclude alembic
py.test --verbose --cov ./unicore/comments unicore/comments
