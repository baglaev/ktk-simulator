from pathlib import Path

from app.domain import ScenarioConfig


DATA_DIR = Path(__file__).resolve().parent / "data"
N1A_SCENARIO_PATH = DATA_DIR / "n1a_developing_fault.json"


def load_scenario_config(path: Path) -> ScenarioConfig:
    """Load and validate a versioned scenario JSON file."""

    return ScenarioConfig.model_validate_json(path.read_text(encoding="utf-8"))


def load_n1a_scenario() -> ScenarioConfig:
    return load_scenario_config(N1A_SCENARIO_PATH)
