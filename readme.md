# cPRArgentina

cPRArgentina is a web-based cPRA calculator built from HLA data derived from deceased donor records from Argentina. It estimates cPRA by directly comparing unacceptable HLA antigens against individual donors in the dataset rather than using population-frequency models. ABO compatibility can also be incorporated optionally, allowing HLA-only and HLA+ABO estimates to be examined separately.

## License

This repository is distributed under a non-commercial license. Research, educational, and academic use is allowed. Commercial use requires prior written permission. See [LICENSE](LICENSE).

## Current scope

- Prototype for research, methodological validation, and educational use
- Not intended for direct clinical decision-making without independent validation
- Single active calculation method: donor filtering
- Optional ABO compatibility
- Dynamic denominator when supported HLA-DQ antigens are present
- Antigen validation against `data/hla_validation.csv`

## Technical information

- Programming language: Python
- Web framework: FastAPI
- Frontend: HTML, CSS, and JavaScript
- Database: SQLite
- Platform: platform-independent, web-based
- Current deployment: PythonAnywhere
- License and restrictions: non-commercial research, educational, and academic use; commercial use requires prior written permission; see [LICENSE](LICENSE)

## Project structure

- `main.py`: FastAPI application, database loading, input validation, and endpoints
- `cpra_logic.py`: helper functions for donor filtering and ABO compatibility logic
- `frontend/index.html`: HTML/CSS/JavaScript frontend served by the application
- `load_donors.py`: incremental loading or full rebuild of `cpra.db` from CSV input
- `data/hla_validation.csv`: HLA antigen validation table
- `tests/test_cpra.py`: automated test suite using `pytest`
- `asgi.py`: ASGI entry point used for the PythonAnywhere deployment
- `scripts/run_cohort.py`: auxiliary script used to reproduce the simulated cohort analysis described in the manuscript

## Current calculation logic

The application works strictly with supported split antigens. User-entered antigens are normalized, classified, and then used to build an HLA incompatibility mask over the evaluable donor pool.

ABO compatibility is optional:

- if `abo_enabled=true`, cPRA is calculated using the union of HLA incompatibility and ABO incompatibility
- if `abo_enabled=false`, the calculation uses HLA incompatibility only

When at least one supported HLA-DQ antigen is entered:

- the denominator is restricted to donors with complete HLA-A, HLA-B, HLA-DR, and HLA-DQ typing

When no supported HLA-DQ antigen is entered:

- the denominator is the full active donor database in `cpra.db`

## Antigen normalization and validation

Entered antigens are classified into four groups:

- supported: used in the calculation
- recognized but unsupported: ignored for calculation and returned as warnings
- broad: ignored for calculation and returned as warnings
- invalid: block calculation and return an error

The reference table is `data/hla_validation.csv`. An antigen may be valid even if it is not observed in the currently loaded donor database.

## Main endpoints

- `GET /`: frontend
- `POST /calc_cpra`: main calculation endpoint
- `GET /health`: basic status endpoint
- `GET /dataset_info`: metadata about the loaded donor database
- `GET /reference_data`: observed antigens, supported antigens, and validation alerts
- `POST /reload_db`: reloads the database into memory

## Local execution

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start the application:

```bash
uvicorn main:app --reload
```

3. Open:

```text
http://127.0.0.1:8000
```

By default, the application uses `cpra.db`.

## Environment variables

- `CPRA_DB`: name or path of the SQLite database file to load. Default: `cpra.db`
- `CPRA_CORS_ORIGINS`: comma-separated list of allowed origins. Default: `*`

## Donor database loading or rebuild

`load_donors.py` supports both the earlier CSV format and the current donor CSV format.

Incremental load:

```bash
python load_donors.py --csv "path/to/donors.csv" --mode append --db cpra.db
```

Full rebuild:

```bash
python load_donors.py --csv "path/to/donors.csv" --mode rebuild --db cpra.db
```

In `append` mode, only new `donor_id` values are added. In `rebuild` mode, `cpra.db` is reconstructed and a previous `.bak` backup is created first.

Dataset distribution and reconstruction instructions for public release will be finalized separately.

## Automated tests

Run the test suite:

```bash
pytest
```

Measure coverage:

```bash
pytest --cov=main --cov=cpra_logic --cov-report=term-missing
```

The current suite covers antigen classification, DQ denominator selection, HLA-only calculation, HLA+ABO calculation, and metadata endpoints.

## Manuscript reproducibility

`scripts/run_cohort.py` is not part of the production application. It is an auxiliary reproducibility script used to recalculate the cohort of 100 simulated profiles described in the manuscript.

What it does:

- runs 100 predefined simulated profiles
- calculates one HLA-only result and one HLA+ABO result for each profile
- writes a CSV file containing the results and denominator metadata

Dependencies:

```bash
pip install -r requirements-dev.txt
```

Execution:

1. Start the application locally:

```bash
uvicorn main:app --reload
```

2. In a separate terminal, run:

```bash
python scripts/run_cohort.py
```

The endpoint can also be overridden through `CPRA_COHORT_URL`.

Example on Linux/macOS:

```bash
export CPRA_COHORT_URL="http://127.0.0.1:8000/calc_cpra"
python scripts/run_cohort.py
```

Example on Windows PowerShell:

```powershell
$env:CPRA_COHORT_URL="http://127.0.0.1:8000/calc_cpra"
python scripts/run_cohort.py
```

The script generates:

- `scripts/resultados_cpra.csv`

CSV columns:

- `ID`
- `ABO`
- `N_antigenos`
- `cPRA_HLA`
- `cPRA_HLA_ABO`
- `donors_evaluated_hla`
- `total_donors_hla`
- `dq_denominator_used_hla`
- `denominator_message_hla`
- `donors_evaluated_hla_abo`
- `total_donors_hla_abo`
- `dq_denominator_used_hla_abo`
- `denominator_message_hla_abo`

The 100 simulated profiles encoded in `scripts/run_cohort.py` were verified against Supplementary Table 2 of the manuscript. The current code reproduced all 100 HLA-only and HLA+ABO results used in the manuscript without discrepancies.

Profiles containing supported HLA-DQ antigens use the DQ-typed donor subset as the denominator. For descriptive analysis, HLA-only cPRA was grouped as `Low` (`<30%`), `Intermediate` (`30-69%`), and `High` (`>=70%`). These strata were used only for descriptive analysis in the manuscript and are not intended as validated clinical thresholds.

## PythonAnywhere deployment

The current production deployment uses `asgi.py` as the application entry point and `cpra.db` as the active donor database.

Operational deployment notes are maintained in `pythonanywhere_runbook.txt`.

## Research-use disclaimer

Research Use Only.

This tool is intended for research, methodological validation, and educational purposes. It does not replace clinical judgment or independent validation.
