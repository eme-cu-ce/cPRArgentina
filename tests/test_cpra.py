from contextlib import contextmanager
from pprint import pformat

import pandas as pd
import pytest
from fastapi import HTTPException

from main import (
    InputData,
    app,
    build_full_dq_donor_mask,
    build_hla_alerts,
    calc_cpra,
    classify_antigens,
    dataset_info,
    get_hla_columns,
    normalize_hla_value,
    reference_data,
)


@contextmanager
def override_app_state(
    *,
    df: pd.DataFrame,
    supported_antigens: set[str],
    last_update: str = "2026-06-18 12:00:00",
):
    original_state = {
        "df": getattr(app.state, "df", None),
        "supported_antigens": getattr(app.state, "supported_antigens", None),
        "hla_columns": getattr(app.state, "hla_columns", None),
        "observed_antigens": getattr(app.state, "observed_antigens", None),
        "total_donors": getattr(app.state, "total_donors", None),
        "last_update": getattr(app.state, "last_update", None),
        "db_path": getattr(app.state, "db_path", None),
        "hla_alerts": getattr(app.state, "hla_alerts", None),
        "full_dq_donor_mask": getattr(app.state, "full_dq_donor_mask", None),
        "total_full_dq_donors": getattr(app.state, "total_full_dq_donors", None),
    }

    df_local = df.copy()
    columnas_hla = get_hla_columns(df_local.columns.tolist())
    app.state.df = df_local
    app.state.supported_antigens = supported_antigens
    app.state.hla_columns = columnas_hla
    app.state.observed_antigens = {
        antigen
        for antigen in df_local[columnas_hla].stack().dropna().unique()
        if antigen and antigen != "-"
    }
    app.state.total_donors = len(df_local)
    app.state.last_update = last_update
    app.state.db_path = "test.db"
    app.state.hla_alerts = build_hla_alerts(df_local.copy(), df_local.copy(), columnas_hla, supported_antigens)
    app.state.full_dq_donor_mask = build_full_dq_donor_mask(df_local)
    app.state.total_full_dq_donors = int(app.state.full_dq_donor_mask.sum())

    try:
        yield
    finally:
        for key, value in original_state.items():
            setattr(app.state, key, value)


def build_test_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "donor_id": "D1",
                "sexo": "F",
                "edad": "35",
                "fecha_operativo": "2026-01-01",
                "A1": "A2",
                "A2": "A11",
                "B1": "B44",
                "B2": "B35",
                "DRB1_1": "DR17",
                "DRB1_2": "DR4",
                "DQB1_1": "DQ7",
                "DQB1_2": "DQ5",
                "abo": "A",
                "rh": "+",
            },
            {
                "donor_id": "D2",
                "sexo": "M",
                "edad": "40",
                "fecha_operativo": "2026-01-02",
                "A1": "A1",
                "A2": "A3",
                "B1": "B8",
                "B2": "B18",
                "DRB1_1": "DR4",
                "DRB1_2": "DR15",
                "DQB1_1": "DQ5",
                "DQB1_2": "DQ6",
                "abo": "B",
                "rh": "+",
            },
            {
                "donor_id": "D3",
                "sexo": "F",
                "edad": "29",
                "fecha_operativo": "2026-01-03",
                "A1": "A24",
                "A2": "A26",
                "B1": "B44",
                "B2": "B60",
                "DRB1_1": "DR17",
                "DRB1_2": "DR11",
                "DQB1_1": "DQ7",
                "DQB1_2": "DQ8",
                "abo": "O",
                "rh": "-",
            },
            {
                "donor_id": "D4",
                "sexo": "M",
                "edad": "51",
                "fecha_operativo": "2026-01-04",
                "A1": "A2",
                "A2": "A29",
                "B1": "B7",
                "B2": "B62",
                "DRB1_1": "DR1",
                "DRB1_2": "DR13",
                "DQB1_1": "",
                "DQB1_2": "",
                "abo": "AB",
                "rh": "+",
            },
        ]
    )


SUPPORTED_ANTIGENS = {"A2", "A11", "B44", "B35", "DR17", "DR4", "DQ7", "DQ5", "DQ6", "DQ8", "B76"}


def print_case(name: str, payload: dict, expected: dict, actual: dict):
    print(
        "\n" + "=" * 70 + "\n"
        f"{name}\n"
        f"input:\n{pformat(payload)}\n"
        f"expected output:\n{pformat(expected)}\n"
        f"actual output:\n{pformat(actual)}\n"
        + "=" * 70
    )


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


def test_normalize_hla_value_agrega_prefijo_y_quita_ceros():
    assert normalize_hla_value("A1", "02") == "A2"
    assert normalize_hla_value("B1", "044") == "B44"
    assert normalize_hla_value("DRB1_1", "04") == "DR4"
    assert normalize_hla_value("DQB1_1", "07") == "DQ7"


def test_classify_antigens_separa_supported_unsupported_broad_invalid():
    classified = classify_antigens(
        ["A2", "Cw7", "DR52", "DPB1*04", "DR3", "DQ1", "banana"],
        SUPPORTED_ANTIGENS,
    )
    assert classified["supported"] == ["A2"]
    assert classified["unsupported"] == ["CW7", "DR52", "DPB1*04"]
    assert classified["broad"] == ["DR3", "DQ1"]
    assert classified["invalid"] == ["BANANA"]


def test_dataset_info_and_reference_data_still_expose_metadata():
    df = build_test_df()
    with override_app_state(df=df, supported_antigens=SUPPORTED_ANTIGENS):
        info = dataset_info()
        data = reference_data()

    assert info["total_donors"] == 4
    assert "A1" in info["hla_columns"]
    assert data["hla_columns"] == ["A1", "A2", "B1", "B2", "DRB1_1", "DRB1_2", "DQB1_1", "DQB1_2"]
    assert "A2" in data["observed_antigens"]


def test_scenario_a_supported_only_uses_entire_database():
    df = build_test_df()
    payload = {"antigenos": ["A2", "B44", "DR17"], "abo": "A", "abo_enabled": True}
    with override_app_state(df=df, supported_antigens=SUPPORTED_ANTIGENS):
        response = calc_cpra(InputData(**payload))

    expected = {
        "N_donors": 4,
        "total_donors": 4,
        "dq_denominator_used": False,
        "warnings": [],
        "cPRA": 100.0,
    }
    print_case("scenario_a", payload, expected, response)
    assert response["N_donors"] == 4
    assert response["total_donors"] == 4
    assert response["dq_denominator_used"] is False
    assert response["warnings"] == []
    assert response["cPRA"] == 100.0


def test_scenario_b_supported_dq_uses_abdrdq_denominator():
    df = build_test_df()
    payload = {"antigenos": ["A2", "DQ7"], "abo": "A", "abo_enabled": True}
    with override_app_state(df=df, supported_antigens=SUPPORTED_ANTIGENS):
        response = calc_cpra(InputData(**payload))

    expected = {
        "N_donors": 3,
        "total_donors": 4,
        "dq_denominator_used": True,
        "denominator_message_contains": "tipificacion completa para HLA-A, HLA-B, HLA-DR y HLA-DQ",
        "cPRA": 100.0,
    }
    print_case("scenario_b", payload, expected, response)
    assert response["N_donors"] == 3
    assert response["total_donors"] == 4
    assert response["dq_denominator_used"] is True
    assert "tipificacion completa para HLA-A, HLA-B, HLA-DR y HLA-DQ" in response["denominator_message"]
    assert response["cPRA"] == 100.0


def test_scenario_c_unsupported_antigens_are_ignored_with_warning():
    df = build_test_df()
    payload = {"antigenos": ["A2", "B44", "Cw7", "DR52", "DPB1*04"], "abo": "A", "abo_enabled": True}
    with override_app_state(df=df, supported_antigens=SUPPORTED_ANTIGENS):
        response = calc_cpra(InputData(**payload))

    expected = {
        "supported_antigens_used": ["A2", "B44"],
        "unsupported_antigens": ["CW7", "DR52", "DPB1*04"],
        "broad_antigens": [],
        "warning_count": 1,
        "N_donors": 4,
    }
    print_case("scenario_c", payload, expected, response)
    assert response["supported_antigens_used"] == ["A2", "B44"]
    assert response["unsupported_antigens"] == ["CW7", "DR52", "DPB1*04"]
    assert response["broad_antigens"] == []
    assert len(response["warnings"]) == 1
    assert "no fueron tomados en cuenta" in response["warnings"][0]
    assert response["N_donors"] == 4


def test_scenario_d_supported_dq_plus_unsupported():
    df = build_test_df()
    payload = {"antigenos": ["DQ7", "Cw7", "DR52"], "abo": "AB", "abo_enabled": True}
    with override_app_state(df=df, supported_antigens=SUPPORTED_ANTIGENS):
        response = calc_cpra(InputData(**payload))

    expected = {
        "supported_antigens_used": ["DQ7"],
        "unsupported_antigens": ["CW7", "DR52"],
        "dq_denominator_used": True,
        "N_donors": 3,
        "cPRA": 66.7,
    }
    print_case("scenario_d", payload, expected, response)
    assert response["supported_antigens_used"] == ["DQ7"]
    assert response["unsupported_antigens"] == ["CW7", "DR52"]
    assert response["dq_denominator_used"] is True
    assert response["N_donors"] == 3
    assert response["cPRA"] == 66.7


def test_scenario_e_broad_only_blocks_calculation_with_warning():
    df = build_test_df()
    payload = {"antigenos": ["DR3", "DQ1", "B5"], "abo": "A", "abo_enabled": True}
    with override_app_state(df=df, supported_antigens=SUPPORTED_ANTIGENS):
        with pytest.raises(HTTPException) as exc_info:
            calc_cpra(InputData(**payload))

    actual = exc_info.value.detail
    expected = {
        "status_code": 400,
        "message_contains": "No se ingresaron antigenos compatibles con el alcance actual de la herramienta",
        "warning_count": 1,
        "warning_contains": "antigenos broad",
    }
    print_case("scenario_e", payload, expected, actual)
    assert exc_info.value.status_code == 400
    assert "No se ingresaron antigenos compatibles con el alcance actual de la herramienta" in actual["message"]
    assert len(actual["warnings"]) == 1
    assert "antigenos broad" in actual["warnings"][0]


def test_scenario_f_invalid_inputs_block_calculation():
    df = build_test_df()
    payload = {"antigenos": ["banana", "AQ7"], "abo": "A", "abo_enabled": True}
    with override_app_state(df=df, supported_antigens=SUPPORTED_ANTIGENS):
        with pytest.raises(HTTPException) as exc_info:
            calc_cpra(InputData(**payload))

    actual = exc_info.value.detail
    expected = {
        "status_code": 400,
        "message_contains": "entradas invalidas",
        "invalid_antigens": ["BANANA", "AQ7"],
    }
    print_case("scenario_f", payload, expected, actual)
    assert exc_info.value.status_code == 400
    assert "entradas invalidas" in actual["message"]
    assert actual["invalid_antigens"] == ["BANANA", "AQ7"]


def test_hla_only_mode_works_when_abo_disabled():
    df = build_test_df()
    payload = {"antigenos": ["A2", "B44"], "abo": None, "abo_enabled": False}
    with override_app_state(df=df, supported_antigens=SUPPORTED_ANTIGENS):
        response = calc_cpra(InputData(**payload))

    expected = {
        "N_donors": 4,
        "total_donors": 4,
        "abo_enabled": False,
        "cPRA": 75.0,
    }
    print_case("hla_only_abo_disabled", payload, expected, response)
    assert response["N_donors"] == 4
    assert response["total_donors"] == 4
    assert response["abo_enabled"] is False
    assert response["cPRA"] == 75.0
