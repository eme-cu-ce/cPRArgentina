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
    load_data_from_db,
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


def test_dataset_info_expone_metadata_hla():
    info = dataset_info()

    assert info["total_donors"] > 0
    assert "A1" in info["hla_columns"]
    assert info["valid_antigen_count"] > 0


def test_reference_data_no_expone_valores_no_hla():
    data = reference_data()

    assert "A2" in data["valid_antigens"]
    assert "M" not in data["valid_antigens"]
    assert data["hla_columns"] == ["A1", "A2", "B1", "B2", "DRB1_1", "DRB1_2", "DQB1_1", "DQB1_2"]


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
