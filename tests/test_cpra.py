import os
import sys
from pprint import pformat

import pandas as pd
from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cpra_logic import build_abo_mask
from main import (
    InputData,
    app,
    build_hla_alerts,
    calc_cpra,
    dataset_info,
    get_hla_columns,
    is_supported_antigen,
    load_supported_antigens,
    load_data_from_db,
    normalize_hla_value,
    reference_data,
)


load_data_from_db(app)


def run_original_filter_only_logic(antigenos: list[str], abo: str | None, abo_enabled: bool) -> dict:
    df_local = app.state.df
    columnas_hla = app.state.hla_columns
    supported_antigens = app.state.supported_antigens

    antigenos_normalizados = [a.strip().upper() for a in antigenos if a and a.strip()]
    abo = abo.upper() if abo else None

    invalid = [a for a in antigenos_normalizados if not is_supported_antigen(a, supported_antigens)]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Antigenos invalidos: {invalid}")

    if abo_enabled and not abo:
        raise HTTPException(
            status_code=400,
            detail="Debe seleccionar un grupo sanguineo si la compatibilidad ABO esta activada.",
        )

    mask_hla = df_local[columnas_hla].isin(antigenos_normalizados).any(axis=1)
    if abo_enabled:
        abo_incompatibles = {
            "A": ["B", "AB"],
            "B": ["A", "AB"],
            "O": ["A", "B", "AB"],
            "AB": [],
        }[abo]
        mask_abo = df_local["abo"].isin(abo_incompatibles)
        mask_total = mask_hla | mask_abo
        cpra_final = mask_total.sum() / len(df_local)
    else:
        cpra_final = mask_hla.sum() / len(df_local)

    return {
        "cPRA": round(cpra_final * 100, 1),
        "N_donors": len(df_local),
        "abo_enabled": abo_enabled,
    }


def print_comparison(name: str, inputs: dict, expected: dict, actual: dict):
    print(
        "\n" + "=" * 70 + "\n"
        f"{name}\n"
        f"inputs:\n{pformat(inputs)}\n"
        f"expected:\n{pformat(expected)}\n"
        f"actual:\n{pformat(actual)}\n"
        + "=" * 70
    )


def test_cpra_valido():
    response = calc_cpra(InputData(antigenos=["A2"], abo="A"))

    assert "cPRA" in response
    assert isinstance(response["cPRA"], float)


def test_cpra_invalido():
    try:
        calc_cpra(InputData(antigenos=["BANANA"], abo="A"))
        assert False, "Se esperaba HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 400


def test_cpra_entre_0_y_100():
    data = calc_cpra(InputData(antigenos=["A2"], abo="A"))

    assert 0 <= data["cPRA"] <= 100


def test_agregar_antigeno_no_disminuye_cpra():
    r1 = calc_cpra(InputData(antigenos=["A2"], abo="A"))
    r2 = calc_cpra(InputData(antigenos=["A2", "B44"], abo="A"))

    assert r2["cPRA"] >= r1["cPRA"]


def test_abo_invalido_rechazado():
    with TestClient(app) as client:
        response = client.post(
            "/calc_cpra",
            json={
                "antigenos": ["A2"],
                "abo": "X",
            },
        )

    assert response.status_code == 422


def test_abo_enabled_invalido_rechazado_por_pydantic():
    with TestClient(app) as client:
        response = client.post(
            "/calc_cpra",
            json={
                "antigenos": ["A2"],
                "abo": "A",
                "abo_enabled": "banana",
            },
        )

    assert response.status_code == 422


def test_abo_requerido_si_esta_activado():
    with TestClient(app) as client:
        response = client.post(
            "/calc_cpra",
            json={
                "antigenos": ["A2"],
                "abo_enabled": True,
            },
        )

    assert response.status_code == 400


def test_health_endpoint_responde_ok():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dataset_info_expone_metadata_hla():
    info = dataset_info()

    assert info["total_donors"] > 0
    assert "A1" in info["hla_columns"]
    assert info["valid_antigen_count"] > 0
    assert info["supported_antigen_count"] > 0


def test_reference_data_no_expone_valores_no_hla():
    data = reference_data()

    assert "A2" in data["observed_antigens"]
    assert "M" not in data["observed_antigens"]
    assert "-" not in data["observed_antigens"]
    assert "B76" in data["supported_antigens"]
    assert data["hla_columns"] == ["A1", "A2", "B1", "B2", "DRB1_1", "DRB1_2", "DQB1_1", "DQB1_2"]
    assert "hla_validation.csv" in data["validation_rule"]


def test_get_hla_columns_devuelve_columnas_esperadas():
    columns = [
        "donor_id",
        "sexo",
        "edad",
        "fecha_operativo",
        "A1",
        "A2",
        "B1",
        "DQB1_1",
        "abo",
        "rh",
    ]

    assert get_hla_columns(columns) == ["A1", "A2", "B1", "DQB1_1"]


def test_normalize_hla_value_agrega_prefijo_y_quita_ceros_a_la_izquierda():
    assert normalize_hla_value("A1", "02") == "A2"
    assert normalize_hla_value("B1", "044") == "B44"
    assert normalize_hla_value("DRB1_1", "04") == "DR4"
    assert normalize_hla_value("DQB1_1", "07") == "DQ7"


def test_normalize_hla_value_respeta_formato_ya_normalizado_y_homocigosis():
    assert normalize_hla_value("A1", "A2") == "A2"
    assert normalize_hla_value("DRB1_1", "DR1404") == "DR1404"
    assert normalize_hla_value("DQB1_1", "-") == "-"


def test_build_hla_alerts_detecta_normalizaciones_y_antigenos_fuera_de_catalogo():
    df_raw = pd.DataFrame(
        {
            "A1": ["2", "11"],
            "B1": ["44", "999"],
        }
    )
    df_normalized = pd.DataFrame(
        {
            "A1": ["A2", "A11"],
            "B1": ["B44", "B999"],
        }
    )

    alerts = build_hla_alerts(
        df_raw=df_raw,
        df_normalized=df_normalized,
        columnas_hla=["A1", "B1"],
        supported_antigens={"A2", "A11", "B44"},
    )

    assert alerts["normalized_value_count"] == 4
    assert alerts["unsupported_observed_antigens"] == ["B999"]
    assert len(alerts["warnings"]) == 2


def test_antigeno_valido_aunque_no_aparezca_en_la_base():
    supported_antigens = load_supported_antigens()
    assert is_supported_antigen("B76", supported_antigens)
    response = calc_cpra(InputData(antigenos=["B76"], abo="A"))
    assert "cPRA" in response


def test_antigeno_con_formato_invalido_se_rechaza():
    try:
        calc_cpra(InputData(antigenos=["BANANA"], abo="A"))
        assert False, "Se esperaba HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 400


def test_build_abo_mask_matches_expected_groups():
    df = pd.DataFrame({"abo": ["A", "B", "AB", "O"]})
    mask = build_abo_mask(df, ["B", "AB"])
    assert mask.tolist() == [False, True, True, False]


def test_filter_only_equivalence_single_antigen_abo_on():
    inputs = {"antigenos": ["A2"], "abo": "A", "abo_enabled": True}
    expected = run_original_filter_only_logic(**inputs)
    actual = calc_cpra(InputData(**inputs))
    print_comparison("single_antigen_abo_on", inputs, expected, actual)
    assert abs(expected["cPRA"] - actual["cPRA"]) < 1e-9
    assert expected["N_donors"] == actual["N_donors"]
    assert expected["abo_enabled"] == actual["abo_enabled"]


def test_filter_only_equivalence_multiple_antigens_abo_on():
    inputs = {"antigenos": ["A2", "B44", "DR4"], "abo": "O", "abo_enabled": True}
    expected = run_original_filter_only_logic(**inputs)
    actual = calc_cpra(InputData(**inputs))
    print_comparison("multiple_antigens_abo_on", inputs, expected, actual)
    assert abs(expected["cPRA"] - actual["cPRA"]) < 1e-9
    assert expected["N_donors"] == actual["N_donors"]
    assert expected["abo_enabled"] == actual["abo_enabled"]


def test_filter_only_equivalence_ab_recipient_no_abo_incompatibility():
    inputs = {"antigenos": ["B76"], "abo": "AB", "abo_enabled": True}
    expected = run_original_filter_only_logic(**inputs)
    actual = calc_cpra(InputData(**inputs))
    print_comparison("ab_recipient_abo_on", inputs, expected, actual)
    assert abs(expected["cPRA"] - actual["cPRA"]) < 1e-9


def test_filter_only_equivalence_highly_incompatible_profile():
    inputs = {"antigenos": ["A2", "A11", "B44", "B35", "DR4", "DQ7"], "abo": "O", "abo_enabled": True}
    expected = run_original_filter_only_logic(**inputs)
    actual = calc_cpra(InputData(**inputs))
    print_comparison("highly_incompatible_abo_on", inputs, expected, actual)
    assert abs(expected["cPRA"] - actual["cPRA"]) < 1e-9


def test_filter_only_equivalence_hla_only_abo_off():
    inputs = {"antigenos": ["A2", "B44"], "abo": None, "abo_enabled": False}
    expected = run_original_filter_only_logic(**inputs)
    actual = calc_cpra(InputData(**inputs))
    print_comparison("hla_only_abo_off", inputs, expected, actual)
    assert abs(expected["cPRA"] - actual["cPRA"]) < 1e-9
    assert expected["N_donors"] == actual["N_donors"]
    assert expected["abo_enabled"] == actual["abo_enabled"]
