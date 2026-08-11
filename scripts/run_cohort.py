import csv
import os
import time

import requests


# URL de la app
URL = os.getenv("CPRA_COHORT_URL", "http://127.0.0.1:8000/calc_cpra")

# Cohorte de 100 perfiles simulados usados para la reproducibilidad del manuscrito
cohorte = [
    ("P001", ["A2"], "O"),
    ("P002", ["B44"], "A"),
    ("P003", ["DR4"], "O"),
    ("P004", ["A24"], "B"),
    ("P005", ["B8"], "O"),
    ("P006", ["DR7"], "A"),
    ("P007", ["DQ5"], "O"),
    ("P008", ["DQ7"], "A"),
    ("P009", ["A2", "B44"], "O"),
    ("P010", ["A24", "DR4"], "A"),

    ("P011", ["A2", "B44"], "O"),
    ("P012", ["A24", "B8"], "A"),
    ("P013", ["A1", "B7", "B35"], "O"),
    ("P014", ["A2", "A24", "B44", "B8"], "B"),
    ("P015", ["A3", "B7"], "O"),

    ("P016", ["DR4"], "O"),
    ("P017", ["DR17", "DR7"], "A"),
    ("P018", ["DR4", "DR7", "DQ7"], "O"),
    ("P019", ["DR17", "DQ2", "DQ8"], "B"),
    ("P020", ["DR4", "DR7", "DR17", "DQ2", "DQ7"], "O"),

    ("P021", ["DQ2"], "O"),
    ("P022", ["DQ7", "DQ8"], "A"),
    ("P023", ["DQ5", "DQ6", "DQ7"], "O"),

    ("P024", ["A2", "B44", "DR4"], "O"),
    ("P025", ["A24", "B8", "DR17"], "A"),
    ("P026", ["A1", "B8", "DR7"], "O"),
    ("P027", ["A3", "B7", "DR4"], "B"),
    ("P028", ["A2", "DR17", "DQ7"], "O"),

    ("P029", ["B44", "DR4", "DQ8"], "A"),
    ("P030", ["A11", "B35", "DR4"], "O"),
    ("P031", ["A2", "B8", "DR17"], "O"),
    ("P032", ["A24", "B44", "DR7"], "A"),
    ("P033", ["B8", "DR17", "DQ2"], "O"),

    ("P034", ["A1", "B7", "DR1"], "A"),
    ("P035", ["A2", "A24", "B44"], "O"),
    ("P036", ["B8", "B44", "DR17"], "O"),
    ("P037", ["A3", "B7", "DR7"], "B"),
    ("P038", ["A2", "B8", "DR4"], "O"),

    ("P039", ["A24", "B35", "DR17"], "A"),
    ("P040", ["A1", "DR17", "DQ2"], "O"),
    ("P041", ["B44", "DR17", "DR7"], "O"),
    ("P042", ["A2", "B8", "DR7"], "A"),
    ("P043", ["A11", "DR4", "DQ7"], "O"),

    ("P044", ["A2", "A3", "DR4"], "O"),
    ("P045", ["B7", "B8", "DR17"], "A"),
    ("P046", ["A24", "B44", "DR17"], "O"),
    ("P047", ["A2", "B35", "DR4"], "O"),
    ("P048", ["A1", "B8", "DR4"], "A"),

    ("P049", ["B44", "DR4", "DR17"], "O"),
    ("P050", ["A3", "DR17", "DQ7"], "B"),
    ("P051", ["A2", "B8", "DR17"], "O"),
    ("P052", ["A24", "B7", "DR4"], "A"),
    ("P053", ["B8", "DR4", "DR7"], "O"),

    ("P054", ["A1", "B35", "DR17"], "O"),
    ("P055", ["A2", "DR17", "DR4"], "A"),
    ("P056", ["B44", "DR7", "DR17"], "O"),
    ("P057", ["A24", "DR4", "DR7"], "O"),
    ("P058", ["A2", "B8", "DR4"], "O"),

    ("P059", ["A2", "DR17", "DQ2"], "O"),
    ("P060", ["A24", "DR4", "DQ8"], "A"),

    ("P061", ["A2", "A24", "B44", "B8", "DR17", "DR4"], "O"),
    ("P062", ["A1", "B8", "DR4", "DR7"], "A"),
    ("P063", ["A2", "B44", "B35", "DR17", "DR4"], "O"),
    ("P064", ["A24", "B8", "DR17", "DR7"], "O"),
    ("P065", ["A2", "A24", "B8", "DR4", "DR7"], "A"),

    ("P066", ["A1", "B7", "B35", "DR17", "DR4"], "O"),
    ("P067", ["A3", "B8", "B44", "DR17", "DR7"], "O"),
    ("P068", ["A2", "A11", "B35", "DR4", "DR7"], "A"),
    ("P069", ["A24", "B8", "DR17", "DR4", "DR7"], "O"),
    ("P070", ["A2", "B44", "B8", "DR17", "DR4"], "O"),

    ("P071", ["A1", "A2", "B7", "DR17", "DR4"], "A"),
    ("P072", ["A3", "B35", "DR4", "DR7", "DR17"], "O"),
    ("P073", ["A2", "B8", "B44", "DR17", "DR7"], "O"),
    ("P074", ["A24", "B7", "DR4", "DR17", "DR7"], "B"),
    ("P075", ["A2", "A3", "B8", "DR4", "DR7"], "O"),

    ("P076", ["A1", "B44", "DR17", "DR4", "DR7"], "O"),
    ("P077", ["A24", "B8", "DR17", "DR4"], "A"),
    ("P078", ["A2", "B35", "DR4", "DR7", "DR17"], "O"),
    ("P079", ["A3", "B8", "DR17", "DR7"], "O"),
    ("P080", ["A2", "A24", "B44", "DR4", "DR7"], "A"),

    ("P081", ["A1", "B8", "DR17", "DR4", "DR7"], "O"),
    ("P082", ["A2", "B44", "DR17", "DR7"], "O"),
    ("P083", ["A24", "B35", "DR4", "DR7"], "A"),
    ("P084", ["A3", "B8", "DR17", "DR4"], "O"),
    ("P085", ["A2", "B8", "DR17", "DR7"], "O"),

    ("P086", ["A1", "B7", "DR4", "DR7"], "B"),
    ("P087", ["A24", "B44", "DR17", "DR4"], "O"),
    ("P088", ["A2", "B8", "DR17", "DR4"], "O"),
    ("P089", ["A3", "B35", "DR7", "DR17"], "A"),
    ("P090", ["A2", "A24", "B8", "DR4", "DR7"], "O"),

    ("P091", ["A2"], "AB"),
    ("P092", ["A2", "B44"], "AB"),
    ("P093", ["A2", "B44", "DR4"], "AB"),
    ("P094", ["A2", "A24", "B44", "B8", "DR17", "DR4"], "AB"),
    ("P095", ["A1", "A2", "A3", "B7", "B8", "B44", "DR17", "DR4", "DR7"], "O"),

    ("P096", ["DR4"], "AB"),
    ("P097", ["B44"], "AB"),
    ("P098", ["A24", "DR7"], "AB"),
    ("P099", ["A2", "B8", "DR17", "DR4", "DR7", "DQ2", "DQ7"], "AB"),
    ("P100", ["A1", "B7", "DR4", "DR7"], "O"),
]

resultados = []
debug_dq_logged = False
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "resultados_cpra.csv")


def extraer_campos_denominador(response_json: dict, suffix: str) -> dict:
    return {
        f"donors_evaluated_{suffix}": response_json.get("N_donors"),
        f"total_donors_{suffix}": response_json.get("total_donors"),
        f"dq_denominator_used_{suffix}": response_json.get("dq_denominator_used"),
        f"denominator_message_{suffix}": response_json.get("denominator_message"),
    }


for pid, antigens, abo in cohorte:
    try:
        # HLA only
        r1 = requests.post(URL, json={
            "antigenos": antigens,
            "abo": "O",  # dummy valido
            "abo_enabled": False
        })
        r1.raise_for_status()
        data_hla = r1.json()
        cpra_hla = data_hla["cPRA"]

        # HLA + ABO
        r2 = requests.post(URL, json={
            "antigenos": antigens,
            "abo": abo,
            "abo_enabled": True
        })
        r2.raise_for_status()
        data_hla_abo = r2.json()
        cpra_abo = data_hla_abo["cPRA"]

        if (not debug_dq_logged) and any(a.upper().startswith("DQ") for a in antigens):
            print("Respuesta JSON cruda HLA-only con DQ:")
            print(data_hla)
            print("Respuesta JSON cruda HLA+ABO con DQ:")
            print(data_hla_abo)
            debug_dq_logged = True

        fila = {
            "ID": pid,
            "ABO": abo,
            "N_antigenos": len(antigens),
            "cPRA_HLA": cpra_hla,
            "cPRA_HLA_ABO": cpra_abo,
        }
        fila.update(extraer_campos_denominador(data_hla, "hla"))
        fila.update(extraer_campos_denominador(data_hla_abo, "hla_abo"))

        resultados.append(fila)

        print(f"{pid} OK")

        time.sleep(0.2)

    except Exception as e:
        print(f"{pid} ERROR:", e)
        try:
            print("Respuesta:", r1.text)
        except Exception:
            pass


if not resultados:
    print("No se generaron resultados. Revisar errores.")
    raise SystemExit(1)

with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=resultados[0].keys())
    writer.writeheader()
    writer.writerows(resultados)

print(f"Listo. CSV generado en {OUTPUT_PATH}.")
