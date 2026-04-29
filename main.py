from contextlib import asynccontextmanager
from datetime import datetime
from typing import Literal
import os
import sqlite3

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from init_demo_db import create_demo_db

# Base por defecto: demo
DB_NAME = os.getenv("CPRA_DB", "cpra_demo.db")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, DB_NAME)
FRONTEND_PATH = os.path.join(BASE_DIR, "frontend", "index.html")
VALIDATION_TABLE_PATH = os.path.join(BASE_DIR, "data", "hla_validation.csv")
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CPRA_CORS_ORIGINS", "*").split(",")
    if origin.strip()
]
VALID_ABO_GROUPS = {"A", "B", "AB", "O"}
VALID_MODES = {"freq", "filter"}
HLA_COLS = ["A1", "A2", "B1", "B2", "DRB1_1", "DRB1_2", "DQB1_1", "DQB1_2"]
HLA_VALUE_PREFIX = {
    "A1": "A",
    "A2": "A",
    "B1": "B",
    "B2": "B",
    "DRB1_1": "DR",
    "DRB1_2": "DR",
    "DQB1_1": "DQ",
    "DQB1_2": "DQ",
}
ABO_INCOMPATIBILITY = {
    "A": ["B", "AB"],
    "B": ["A", "AB"],
    "O": ["A", "B", "AB"],
    "AB": [],
}

# Ensure first-run startup does not fail when DB/table is missing.
DONORS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS donors (
    donor_id TEXT PRIMARY KEY,
    sexo TEXT,
    edad TEXT,
    fecha_operativo TEXT,
    A1 TEXT,
    A2 TEXT,
    B1 TEXT,
    B2 TEXT,
    DRB1_1 TEXT,
    DRB1_2 TEXT,
    DQB1_1 TEXT,
    DQB1_2 TEXT,
    abo TEXT,
    rh TEXT
);
"""


def get_hla_columns(columns: list[str]) -> list[str]:
    """Return the expected HLA columns that are present in the dataset."""
    return [col for col in HLA_COLS if col in columns]


def load_supported_antigens(validation_table_path: str = VALIDATION_TABLE_PATH) -> set[str]:
    df_validation = pd.read_csv(validation_table_path, dtype=str).fillna("")
    if "antigen" not in df_validation.columns:
        raise ValueError("La tabla de validacion HLA debe incluir la columna 'antigen'.")

    return {
        antigen.strip().upper()
        for antigen in df_validation["antigen"].tolist()
        if antigen.strip()
    }


def is_supported_antigen(antigen: str, supported_antigens: set[str]) -> bool:
    return antigen in supported_antigens


def normalize_hla_value(column: str, value: str) -> str:
    value = str(value).strip().upper()

    if not value or value in {"NAN", "NONE"}:
        return ""

    if value == "-":
        return value

    prefix = HLA_VALUE_PREFIX.get(column)
    if not prefix:
        return value

    normalized = value.replace("*", "").replace(" ", "")
    if normalized.startswith(prefix):
        suffix = normalized[len(prefix):]
    else:
        suffix = normalized

    suffix = suffix.lstrip("0") or "0"
    return f"{prefix}{suffix}"


def normalize_hla_columns(df_local: pd.DataFrame, columnas_hla: list[str]) -> pd.DataFrame:
    for column in columnas_hla:
        df_local[column] = df_local[column].apply(lambda value: normalize_hla_value(column, value))
    return df_local


def build_hla_alerts(
    df_raw: pd.DataFrame,
    df_normalized: pd.DataFrame,
    columnas_hla: list[str],
    supported_antigens: set[str],
) -> dict:
    total_hla_values = 0
    normalized_value_count = 0

    for column in columnas_hla:
        raw_series = df_raw[column].fillna("").astype(str).str.strip().str.upper()
        normalized_series = df_normalized[column].fillna("").astype(str).str.strip().str.upper()

        comparable_mask = raw_series.ne("") & raw_series.ne("-") & raw_series.ne("NAN") & raw_series.ne("NONE")
        total_hla_values += int(comparable_mask.sum())
        normalized_value_count += int((raw_series[comparable_mask] != normalized_series[comparable_mask]).sum())

    observed_antigens = {
        antigen
        for antigen in df_normalized[columnas_hla].stack().dropna().unique()
        if antigen and antigen != "-"
    }
    unsupported_observed_antigens = sorted(observed_antigens - supported_antigens)
    normalized_ratio = (normalized_value_count / total_hla_values) if total_hla_values else 0.0

    warnings = []
    if normalized_value_count:
        warnings.append(
            f"Se normalizaron {normalized_value_count} valores HLA al cargar la base "
            f"({normalized_ratio:.1%} de las celdas HLA con dato)."
        )
    if unsupported_observed_antigens:
        sample = ", ".join(unsupported_observed_antigens[:10])
        warnings.append(
            "Se detectaron antigenos observados fuera de la tabla de validacion HLA: "
            f"{sample}"
        )

    return {
        "warnings": warnings,
        "normalized_value_count": normalized_value_count,
        "total_hla_values": total_hla_values,
        "normalized_value_ratio": round(normalized_ratio, 4),
        "unsupported_observed_antigens": unsupported_observed_antigens,
    }


# =========================
# Funcion reutilizable de carga
# =========================
def load_data_from_db(app: FastAPI):
    """Cargar datos desde SQLite y actualizar app.state."""
    if DB_NAME == "cpra_demo.db" and not os.path.exists(DB_PATH):
        create_demo_db(DB_PATH)

    supported_antigens = load_supported_antigens()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(DONORS_TABLE_SQL)
        df_local = pd.read_sql_query("SELECT * FROM donors", conn)

    for col in df_local.columns:
        df_local[col] = df_local[col].astype(str).str.strip().str.upper()

    df_raw_hla = df_local.copy()

    if "abo" in df_local.columns:
        df_local["abo"] = df_local["abo"].replace({"0": "O"})

    frecuencias_local = df_local["abo"].value_counts(normalize=True).to_dict()
    columnas_hla = get_hla_columns(df_local.columns.tolist())
    df_local = normalize_hla_columns(df_local, columnas_hla)
    hla_alerts = build_hla_alerts(df_raw_hla, df_local, columnas_hla, supported_antigens)
    antigens_observados = {
        antigen
        for antigen in df_local[columnas_hla].stack().dropna().unique()
        if antigen and antigen != "-"
    }

    app.state.df = df_local
    app.state.frecuencias_abo = frecuencias_local
    app.state.observed_antigens = antigens_observados
    app.state.supported_antigens = supported_antigens
    app.state.hla_columns = columnas_hla
    app.state.hla_alerts = hla_alerts
    app.state.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    app.state.total_donors = len(df_local)
    app.state.db_path = DB_PATH

    print("Base recargada. Donantes:", len(df_local))
    for warning in hla_alerts["warnings"]:
        print("ADVERTENCIA HLA:", warning)


# =========================
# Lifespan moderno
# =========================
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_data_from_db(app)
    yield


# =========================
# Crear app
# =========================
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# Modelo de entrada
# =========================
class InputData(BaseModel):
    antigenos: list[str]
    abo: Literal["A", "B", "AB", "O"]
    mode: Literal["freq", "filter"] = "freq"


# =========================
# Endpoint calculo cPRA
# =========================
@app.post("/calc_cpra")
def calc_cpra(data: InputData):
    df_local: pd.DataFrame = getattr(app.state, "df", pd.DataFrame())
    frecuencias_local = getattr(app.state, "frecuencias_abo", {})
    supported_antigens = getattr(app.state, "supported_antigens", set())
    columnas_hla = getattr(app.state, "hla_columns", [])

    if df_local.empty:
        return {"cPRA": 0.0}

    if not columnas_hla:
        raise HTTPException(
            status_code=500,
            detail="La base no contiene columnas HLA configuradas.",
        )

    antigenos = [a.strip().upper() for a in data.antigenos if a and a.strip()]
    abo = data.abo.upper()
    mode = data.mode.lower().strip()

    if not antigenos:
        raise HTTPException(
            status_code=400,
            detail="Debe enviar al menos un antigeno.",
        )

    invalid = [a for a in antigenos if not is_supported_antigen(a, supported_antigens)]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Antigenos invalidos: {invalid}")

    mask_hla = df_local[columnas_hla].isin(antigenos).any(axis=1)
    cpra_hla = mask_hla.sum() / len(df_local)

    abo_incompatibles = ABO_INCOMPATIBILITY[abo]
    freq_abo_incomp = sum(frecuencias_local.get(g, 0) for g in abo_incompatibles)

    if mode == "filter":
        mask_abo = df_local["abo"].isin(abo_incompatibles)
        mask_total = mask_hla | mask_abo
        cpra_final = mask_total.sum() / len(df_local)
    else:
        cpra_final = cpra_hla + ((1 - cpra_hla) * freq_abo_incomp)

    return {
        "cPRA": round(cpra_final * 100, 1),
        "N_donors": len(df_local),
        "mode_used": mode.upper(),
        "last_update": app.state.last_update,
    }


# =========================
# Endpoint recarga en caliente
# =========================
@app.post("/reload_db")
def reload_db():
    load_data_from_db(app)
    return {"status": "Base recargada correctamente"}


@app.get("/health")
def health():
    hla_alerts = getattr(app.state, "hla_alerts", {})
    return {
        "status": "ok",
        "database": os.path.basename(getattr(app.state, "db_path", DB_PATH)),
        "total_donors": getattr(app.state, "total_donors", 0),
        "hla_warning_count": len(hla_alerts.get("warnings", [])),
    }


# =========================
# Endpoint metadata
# =========================
@app.get("/dataset_info")
def dataset_info():
    hla_alerts = getattr(app.state, "hla_alerts", {})
    return {
        "total_donors": getattr(app.state, "total_donors", 0),
        "last_update": getattr(app.state, "last_update", "N/A"),
        "db_path": getattr(app.state, "db_path", DB_PATH),
        "hla_columns": getattr(app.state, "hla_columns", []),
        "valid_antigen_count": len(getattr(app.state, "observed_antigens", set())),
        "supported_antigen_count": len(getattr(app.state, "supported_antigens", set())),
        "hla_warning_count": len(hla_alerts.get("warnings", [])),
        "hla_warnings": hla_alerts.get("warnings", []),
    }


@app.get("/reference_data")
def reference_data():
    observed_antigens = getattr(app.state, "observed_antigens", set())
    supported_antigens = getattr(app.state, "supported_antigens", set())
    hla_alerts = getattr(app.state, "hla_alerts", {})
    return {
        "hla_columns": getattr(app.state, "hla_columns", []),
        "observed_antigens": sorted(observed_antigens),
        "observed_antigen_count": len(observed_antigens),
        "supported_antigens": sorted(supported_antigens),
        "supported_antigen_count": len(supported_antigens),
        "unsupported_observed_antigens": hla_alerts.get("unsupported_observed_antigens", []),
        "normalized_hla_value_count": hla_alerts.get("normalized_value_count", 0),
        "normalized_hla_value_ratio": hla_alerts.get("normalized_value_ratio", 0.0),
        "hla_warnings": hla_alerts.get("warnings", []),
        "abo_groups": sorted(VALID_ABO_GROUPS),
        "modes": sorted(VALID_MODES),
        "validation_rule": "Validated against data/hla_validation.csv",
    }


# =========================
# Servir frontend
# =========================
@app.get("/", response_class=HTMLResponse)
def root_page():
    try:
        with open(FRONTEND_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(content="<h2>Frontend no encontrado</h2>", status_code=404)
