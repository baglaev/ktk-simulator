from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.domain import ParameterOrigin, ScenarioConfig
from app.main import app
from app.scenarios import load_n1a_scenario


client = TestClient(app)


def test_n1a_scenario_catalog_is_valid_and_complete_for_mvp() -> None:
    scenario = load_n1a_scenario()

    assert scenario.scenario_id == "MVP-SC-01"
    assert len(scenario.equipment) == 22
    assert len(scenario.connections) == 15
    assert len(scenario.signals) == 32

    equipment_tags = {item.tag for item in scenario.equipment}
    assert {
        "Р-11",
        "Р-12",
        "Н-1",
        "Н-1А",
        "Н-1Б",
        "Н-1В",
        "Т-1-Т-11",
        "Э-1",
        "Э-2",
        "Э-3",
        "Э-4",
        "Э-5",
        "Э-6",
        "Е-15",
        "К-1",
    }.issubset(equipment_tags)

    signal_ids = {item.signal_id for item in scenario.signals}
    assert {"PRA351", "FYQR117", "LRCA605", "LRCA602"}.issubset(signal_ids)
    assert not any(item.startswith("COMPAX.N1V") for item in signal_ids)


def test_n1a_passport_values_are_source_backed() -> None:
    scenario = load_n1a_scenario()
    n1a = next(item for item in scenario.equipment if item.tag == "Н-1А")
    specifications = {item.parameter_id: item for item in n1a.specifications}

    assert specifications["rated-capacity"].value == 450
    assert specifications["discharge-pressure"].value == 19.5
    assert specifications["motor-power"].value == 400
    assert all(
        item.provenance.origin is ParameterOrigin.SOURCE
        for item in specifications.values()
    )


def test_modelled_signal_representation_is_marked_as_assumption() -> None:
    scenario = load_n1a_scenario()
    pra351 = next(item for item in scenario.signals if item.signal_id == "PRA351")

    assert pra351.provenance.origin is ParameterOrigin.SOURCE
    assert pra351.unit == "percent_of_baseline"
    assert pra351.unit_provenance is not None
    assert (
        pra351.unit_provenance.origin
        is ParameterOrigin.EDUCATIONAL_ASSUMPTION
    )
    assert pra351.unit_provenance.assumption_id == "A-03"


def test_scenario_rejects_unknown_equipment_reference() -> None:
    payload = load_n1a_scenario().model_dump(mode="json", by_alias=True)
    invalid_payload = deepcopy(payload)
    invalid_payload["signals"][0]["equipmentId"] = "eq-missing"

    with pytest.raises(ValidationError, match="unknown signal equipment ID"):
        ScenarioConfig.model_validate(invalid_payload)


def test_scenario_api_returns_catalog_and_model_definition() -> None:
    catalog_response = client.get("/api/v1/scenarios")
    model_response = client.get("/api/v1/scenarios/MVP-SC-01/model-definition")

    assert catalog_response.status_code == 200
    assert catalog_response.json()[0]["scenarioId"] == "MVP-SC-01"
    assert model_response.status_code == 200
    assert model_response.json()["schemaVersion"] == "1.0"
    assert len(model_response.json()["equipment"]) == 22


def test_scenario_api_returns_404_for_unknown_scenario() -> None:
    response = client.get("/api/v1/scenarios/unknown/model-definition")

    assert response.status_code == 404


def test_openapi_contains_scenario_contracts() -> None:
    schemas = client.get("/openapi.json").json()["components"]["schemas"]

    assert "ScenarioConfig" in schemas
    assert "EquipmentDefinition" in schemas
    assert "SignalDefinition" in schemas
