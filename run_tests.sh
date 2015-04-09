#!/bin/bash
set -e

flake8 unicore --exclude alembic
trial --coverage unicore/comments
