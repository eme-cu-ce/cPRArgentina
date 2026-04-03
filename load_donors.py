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


def backup_existing_db(db_name: str) -> str | None:
    if not os.path.exists(db_name):
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_name}.{timestamp}.bak"
    shutil.copy2(db_name, backup_path)
    return backup_path


def load_csv(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, sep=";", dtype=str)

    missing_columns = [column for column in DONOR_COLUMNS if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Faltan columnas obligatorias en el CSV: {missing_columns}")

    df = df[DONOR_COLUMNS].copy()

    for col in df.columns:
        df[col] = df[col].fillna("").astype(str).str.strip().str.upper()

    return df


def append_new_donors_from_csv(csv_path: str, db_name: str = DB_NAME):
    df = load_csv(csv_path)

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
    print(f"Nuevos donantes insertados: {inserted}")
    print(f"Donor_id ya existentes ignorados: {ignored}")


def rebuild_db_from_csv(csv_path: str, db_name: str = DB_NAME, make_backup: bool = True):
    df = load_csv(csv_path)
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
    print(f"Donantes cargados: {len(df)}")
    if backup_path:
        print(f"Backup previo guardado en: {backup_path}")


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
