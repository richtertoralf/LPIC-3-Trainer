#!/usr/bin/env bash
# Create (or refresh) the virtual environment and install the application into it.
# Usage: create-venv.sh <venv-dir> <app-dir>
set -euo pipefail
VENV="${1:?venv directory required}"
APP="${2:?app directory required}"
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install --quiet --upgrade pip
# Editable install: the package stays in $APP so that content/, migrations/ and alembic.ini are found.
# setuptools prints a "BuildBackendWarning: Editable installation" banner for every editable
# install; it is advice for developers, not for administrators, so it is silenced here.
PYTHONWARNINGS="ignore::UserWarning" "$VENV/bin/python" -m pip install --quiet --editable "$APP"
