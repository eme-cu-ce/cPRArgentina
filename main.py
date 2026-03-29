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

# Base por defecto: demo
DB_NAME = os.getenv("CPRA_DB", "cpra_demo.db")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, DB_NAME)
FRONTEND_PATH = os.path.join(BASE_DIR, "frontend", "index.html")
VALID_ABO_GROUPS = {"A", "B", "AB", "O"}
VALID_MODES = {"freq", "filter"}
HLA_COLS = ["A1", "A2", "B1", "B2", "DRB1_1", "DRB1_2", "DQB1_1", "DQB1_2"]
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


# =========================
# Funcion reutilizable de carga
# =========================
def load_data_from_db(app: FastAPI):
    """Cargar datos desde SQLite y actualizar app.state."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(DONORS_TABLE_SQL)
        df_local = pd.read_sql_query("SELECT * FROM donors", conn)

    for col in df_local.columns:
        df_local[col] = df_local[col].astype(str).str.strip().str.upper()

    if "abo" in df_local.columns:
        df_local["abo"] = df_local["abo"].replace({"0": "O"})

    frecuencias_local = df_local["abo"].value_counts(normalize=True).to_dict()
    columnas_hla = get_hla_columns(df_local.columns.tolist())
    antigens_validos = {
        antigen
        for antigen in df_local[columnas_hla].stack().dropna().unique()
        if antigen
    }

    app.state.df = df_local
    app.state.frecuencias_abo = frecuencias_local
    app.state.valid_antigens = antigens_validos
    app.state.hla_columns = columnas_hla
    app.state.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    app.state.total_donors = len(df_local)
    app.state.db_path = DB_PATH

    print("Base recargada. Donantes:", len(df_local))


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
    allow_origins=["*"],
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
    valid_antigens = getattr(app.state, "valid_antigens", set())
    columnas_hla = getattr(app.state, "hla_columns", [])

    if df_local.empty:
        return {"cPRA": 0.0}

    antigenos = [a.strip().upper() for a in data.antigenos if a and a.strip()]
    abo = data.abo.upper()
    mode = data.mode.lower().strip()

    if not antigenos:
        raise HTTPException(
            status_code=400,
            detail="Debe enviar al menos un antigeno.",
        )

    invalid = [a for a in antigenos if a not in valid_antigens]
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


# =========================
# Endpoint metadata
# =========================
@app.get("/dataset_info")
def dataset_info():
    return {
        "total_donors": getattr(app.state, "total_donors", 0),
        "last_update": getattr(app.state, "last_update", "N/A"),
        "db_path": getattr(app.state, "db_path", DB_PATH),
        "hla_columns": getattr(app.state, "hla_columns", []),
        "valid_antigen_count": len(getattr(app.state, "valid_antigens", set())),
    }


@app.get("/reference_data")
def reference_data():
    return {
        "hla_columns": getattr(app.state, "hla_columns", []),
        "valid_antigens": sorted(getattr(app.state, "valid_antigens", set())),
        "abo_groups": sorted(VALID_ABO_GROUPS),
        "modes": sorted(VALID_MODES),
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
