from pathlib import Path

from app.simulation.config import ModelProfile


DATA_DIR = Path(__file__).resolve().parents[1] / "scenarios" / "data"
N1A_MODEL_PROFILE_PATH = DATA_DIR / "n1a_model_profile.json"


def load_model_profile(path: Path) -> ModelProfile:
    return ModelProfile.model_validate_json(path.read_text(encoding="utf-8"))


def load_n1a_model_profile() -> ModelProfile:
    return load_model_profile(N1A_MODEL_PROFILE_PATH)
