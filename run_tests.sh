#!/bin/bash
set -e

flake8 unicore --exclude alembic
trial unicore/comments
