@echo off
REM Windows: create venv (first time), install, generate data, run pipeline and tests.
if not exist .venv (
    python -m venv .venv
)
call .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
python -m retail_etl all
pytest
