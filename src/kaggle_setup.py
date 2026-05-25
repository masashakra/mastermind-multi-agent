# Kaggle Setup Helper
# Loads environment variables from kaggle_setup/.env for remote LLM access

import os
from pathlib import Path


def load_kaggle_env():
    """Load Kaggle environment variables from kaggle_setup/.env file.

    Call this at the start of your program to enable Kaggle backend.

    Example:
        from src.kaggle_setup import load_kaggle_env
        load_kaggle_env()

        # Now you can use provider="kaggle"
        orchestrator = BossWorkerOrchestrator(puzzle, provider="kaggle")
    """
    env_file = Path(__file__).parent.parent / "kaggle_setup" / ".env"

    if not env_file.exists():
        raise FileNotFoundError(f"Kaggle .env file not found at {env_file}")

    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

    # Verify required variables
    if "KAGGLE_URL" not in os.environ:
        raise ValueError("KAGGLE_URL not set in kaggle_setup/.env")

    print(f"✓ Kaggle backend loaded: {os.environ['KAGGLE_URL']}")
