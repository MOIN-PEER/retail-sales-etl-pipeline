#!/usr/bin/env bash
# macOS/Linux: create venv (first time), install, generate data, run pipeline and tests.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
python -m retail_etl all
pytest
