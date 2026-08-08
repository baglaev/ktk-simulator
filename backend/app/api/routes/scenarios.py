from fastapi import APIRouter, HTTPException, status

from app.domain import ScenarioConfig, ScenarioSummary
from app.scenarios import load_n1a_scenario


router = APIRouter(prefix="/api/v1/scenarios", tags=["scenarios"])


@router.get("", response_model=list[ScenarioSummary])
async def list_scenarios() -> list[ScenarioSummary]:
    scenario = load_n1a_scenario()
    return [scenario.to_summary()]


@router.get("/{scenario_id}/model-definition", response_model=ScenarioConfig)
async def get_model_definition(scenario_id: str) -> ScenarioConfig:
    scenario = load_n1a_scenario()
    if scenario.scenario_id != scenario_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )
    return scenario
