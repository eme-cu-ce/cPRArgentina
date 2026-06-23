import argparse
import os
import shutil
import sqlite3
from datetime import datetime

import pandas as pd


DB_NAME = "cpra.db"
CSV_PATH = None

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
)
"""

DONOR_COLUMNS = [
    "donor_id",
    "sexo",
    "edad",
    "fecha_operativo",
    "A1",
    "A2",
    "B1",
    "B2",
    "DRB1_1",
    "DRB1_2",
    "DQB1_1",
    "DQB1_2",
    "abo",
    "rh",
]

OLD_FORMAT_REQUIRED_COLUMNS = [
    "donor_id",
    "fecha_operativo",
    "A1",
    "A2",
    "B1",
    "B2",
    "DRB1_1",
    "DRB1_2",
    "DQB1_1",
    "DQB1_2",
    "abo",
    "rh",
]

REAL_FORMAT_COLUMN_MAP = {
    "id_pk": "donor_id",
    "fecha_hla": "fecha_operativo",
    "A_1": "A1",
    "A_2": "A2",
    "B_1": "B1",
    "B_2": "B2",
    "DRB1_1": "DRB1_1",
    "DRB1_2": "DRB1_2",
    "DQB1_1": "DQB1_1",
    "DQB1_2": "DQB1_2",
    "grupo_sanguineo": "abo",
    "factor_sanguineo": "rh",
}

REAL_FORMAT_REQUIRED_COLUMNS = list(REAL_FORMAT_COLUMN_MAP.keys())
NOT_INFORMATIVE_VALUES = {"", "-", "NAN", "NONE"}


def read_csv_auto(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, sep=None, engine="python", dtype=str, encoding="utf-8-sig")
    df.columns = [
        str(col).replace("\ufeff", "").strip()
        for col in df.columns
    ]
    return df


def detect_csv_format(df: pd.DataFrame) -> str:
    columns = set(df.columns)

    if all(column in columns for column in OLD_FORMAT_REQUIRED_COLUMNS):
        return "old"

    if all(column in columns for column in REAL_FORMAT_REQUIRED_COLUMNS):
        return "real"

    missing_old = [column for column in OLD_FORMAT_REQUIRED_COLUMNS if column not in columns]
    missing_real = [column for column in REAL_FORMAT_REQUIRED_COLUMNS if column not in columns]
    raise ValueError(
        "No se pudo reconocer el formato del CSV.\n"
        f"Formato viejo: faltan {missing_old}\n"
        f"Formato real: faltan {missing_real}"
    )


def normalize_abo(value: str) -> str:
    normalized = str(value).strip().upper()
    if normalized == "0":
        return "O"
    return normalized


def normalize_dataframe_values(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        df[col] = df[col].fillna("").astype(str).str.strip().str.upper()

    if "abo" in df.columns:
        df["abo"] = df["abo"].apply(normalize_abo)

    return df


def is_locus_informative(series_a: pd.Series, series_b: pd.Series) -> pd.Series:
    return ~series_a.isin(NOT_INFORMATIVE_VALUES) | ~series_b.isin(NOT_INFORMATIVE_VALUES)


def summarize_loaded_donors(df: pd.DataFrame) -> None:
    abo_distribution = df["abo"].value_counts(dropna=False).to_dict()

    abdr_complete_mask = (
        is_locus_informative(df["A1"], df["A2"])
        & is_locus_informative(df["B1"], df["B2"])
        & is_locus_informative(df["DRB1_1"], df["DRB1_2"])
    )
    abdrdq_complete_mask = abdr_complete_mask & is_locus_informative(df["DQB1_1"], df["DQB1_2"])

    print(f"Total donors loaded: {len(df)}")
    print(f"ABO distribution: {abo_distribution}")
    print(f"Number of ABDR-complete donors: {int(abdr_complete_mask.sum())}")
    print(f"Number of ABDRDQ-complete donors: {int(abdrdq_complete_mask.sum())}")


def backup_existing_db(db_name: str) -> str | None:
    if not os.path.exists(db_name):
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_name}.{timestamp}.bak"
    shutil.copy2(db_name, backup_path)
    return backup_path


def load_csv(csv_path: str) -> pd.DataFrame:
    df_raw = read_csv_auto(csv_path)
    detected_format = detect_csv_format(df_raw)

    if detected_format == "old":
        df = df_raw.copy()
        missing_columns = [column for column in OLD_FORMAT_REQUIRED_COLUMNS if column not in df.columns]
        if missing_columns:
            raise ValueError(f"Faltan columnas obligatorias en el CSV formato viejo: {missing_columns}")
        for optional_column in ["sexo", "edad"]:
            if optional_column not in df.columns:
                df[optional_column] = ""
        df = df[DONOR_COLUMNS].copy()
    else:
        missing_columns = [column for column in REAL_FORMAT_REQUIRED_COLUMNS if column not in df_raw.columns]
        if missing_columns:
            raise ValueError(f"Faltan columnas obligatorias en el CSV formato real: {missing_columns}")
        df = df_raw.rename(columns=REAL_FORMAT_COLUMN_MAP).copy()
        df["sexo"] = ""
        df["edad"] = ""
        df = df[DONOR_COLUMNS].copy()

    df = normalize_dataframe_values(df)
    df.attrs["detected_format"] = detected_format

    return df


def append_new_donors_from_csv(csv_path: str, db_name: str = DB_NAME):
    df = load_csv(csv_path)
    detected_format = df.attrs.get("detected_format", "unknown")

    inserted = 0
    ignored = 0

    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute(DONORS_TABLE_SQL)

        for row in df.itertuples(index=False, name=None):
            try:
                cursor.execute(
                    """
                    INSERT INTO donors (
                        donor_id, sexo, edad, fecha_operativo,
                        A1, A2, B1, B2,
                        DRB1_1, DRB1_2,
                        DQB1_1, DQB1_2,
                        abo, rh
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    row,
                )
                inserted += 1
            except sqlite3.IntegrityError:
                ignored += 1

        conn.commit()

    print(f"Carga incremental desde {csv_path}")
    print(f"Formato detectado: {detected_format}")
    print(f"Nuevos donantes insertados: {inserted}")
    print(f"Donor_id ya existentes ignorados: {ignored}")
    summarize_loaded_donors(df)


def rebuild_db_from_csv(csv_path: str, db_name: str = DB_NAME, make_backup: bool = True):
    df = load_csv(csv_path)
    detected_format = df.attrs.get("detected_format", "unknown")
    backup_path = backup_existing_db(db_name) if make_backup else None

    if os.path.exists(db_name):
        os.remove(db_name)

    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute(DONORS_TABLE_SQL)
        cursor.executemany(
            """
            INSERT INTO donors (
                donor_id, sexo, edad, fecha_operativo,
                A1, A2, B1, B2,
                DRB1_1, DRB1_2,
                DQB1_1, DQB1_2,
                abo, rh
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            df.itertuples(index=False, name=None),
        )
        conn.commit()

    print(f"Base reconstruida desde {csv_path}")
    print(f"Formato detectado: {detected_format}")
    if backup_path:
        print(f"Backup previo guardado en: {backup_path}")
    summarize_loaded_donors(df)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cargar donantes desde CSV hacia SQLite.")
    parser.add_argument("--csv", default=CSV_PATH, help="Ruta al archivo CSV fuente.")
    parser.add_argument("--db", default=DB_NAME, help="Ruta al archivo SQLite destino.")
    parser.add_argument(
        "--mode",
        choices=["append", "rebuild"],
        default="append",
        help="append: agrega solo donor_id nuevos; rebuild: reconstruye la base desde cero.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Solo aplica a rebuild. Evita crear backup de la base previa.",
    )
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()

    if not args.csv:
        raise SystemExit("Debe indicar la ruta del CSV con --csv.")

    if args.mode == "append":
        append_new_donors_from_csv(csv_path=args.csv, db_name=args.db)
    else:
        rebuild_db_from_csv(
            csv_path=args.csv,
            db_name=args.db,
            make_backup=not args.no_backup,
        )
