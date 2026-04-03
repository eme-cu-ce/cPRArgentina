# cPRArgentina

ABO-adjusted cPRA calculator based on Argentine donor data.

This project is a small FastAPI web app with a built-in HTML frontend. A user can enter unacceptable HLA antigens and an ABO blood group, and the app returns an estimated cPRA based on a local SQLite donor dataset.

## Current scope

- Prototype for research and validation
- Not intended for direct clinical decision-making
- Uses a real or demo SQLite dataset
- Includes two calculation modes: `freq` and `filter`
- Validates antigens against `data/hla_validation.csv`

## Main endpoints

- `GET /` serves the frontend
- `POST /calc_cpra` calculates cPRA
- `GET /dataset_info` returns dataset metadata
- `GET /reference_data` returns observed and supported HLA antigens
- `GET /health` returns a simple health response
- `POST /reload_db` reloads the database into memory

## Local run

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the app:

```bash
uvicorn main:app --reload
```

3. Open:

```text
http://127.0.0.1:8000
```

## Database selection

By default, the app uses `cpra_demo.db`.

To use the real SQLite file:

On Windows `cmd`:

```cmd
set CPRA_DB=cpra.db
uvicorn main:app --reload
```

On Windows PowerShell:

```powershell
$env:CPRA_DB="cpra.db"
uvicorn main:app --reload
```

## Environment variables

- `CPRA_DB`: SQLite database filename or path
- `CPRA_CORS_ORIGINS`: comma-separated allowed origins, default `*`

## Demo dataset

You can recreate the synthetic demo database with:

```bash
python init_demo_db.py
```

If `cpra_demo.db` is missing at startup, the app recreates it automatically.

## Donor loading

Use `load_donors.py` to load a donor CSV into `cpra.db`.

Incremental load:

```bash
python load_donors.py --csv "C:\path\to\donors.csv" --mode append
```

This adds only new `donor_id` values and ignores duplicates already present in the database.

Full rebuild:

```bash
python load_donors.py --csv "C:\path\to\donors.csv" --mode rebuild
```

This recreates `cpra.db` from the CSV and stores a timestamped `.bak` backup first.

## Validation source

The list of accepted HLA antigens is stored in:

- `data/hla_validation.csv`

This validation catalog is separate from the donor database. An antigen can be valid even if it does not appear in the currently loaded donor dataset.

## PythonAnywhere direction

This repo is being prepared for an initial deployment on PythonAnywhere with a real SQLite database.

Practical model:

- code in GitHub
- real `cpra.db` uploaded to the PythonAnywhere account
- app configured to point to that database file

## Keep out of Git

Do not commit:

- the real donor SQLite database
- donor CSV files with real data
- backups such as `.bak`
- generated caches such as `__pycache__` or `.pytest_cache`

## Pre-deploy checklist

- App starts successfully
- `/health` returns `status: ok`
- Frontend loads at `/`
- A valid cPRA example returns a result
- Invalid antigen input returns a readable error
- Real database metadata appears in the interface
- Disclaimer is visible in the UI

## Disclaimer

Research Use Only.

This tool is intended for research, methodological validation, and educational purposes. It is not intended for direct clinical decision-making without independent verification.
