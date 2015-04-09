#!/bin/bash
set -e

flake8 unicore --exclude alembic
coverage run --source=unicore.comments `which trial` unicore/comments
