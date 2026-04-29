import os
import sys

from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import (
    InputData,
    app,
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


def test_mode_invalido_rechazado():
    with TestClient(app) as client:
        response = client.post(
            "/calc_cpra",
            json={
                "antigenos": ["A2"],
                "abo": "A",
                "mode": "banana",
            },
        )

    assert response.status_code == 422


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
