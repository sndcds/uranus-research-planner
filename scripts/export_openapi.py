"""Offline generation without reading environment settings or contacting a provider."""

import json
from pathlib import Path

from research_planner.app import create_app
from research_planner.config import Settings

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    # model_construct avoids environment loading solely for offline schema generation.
    app = create_app(Settings.model_construct())
    (ROOT / "docs" / "openapi.json").write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
