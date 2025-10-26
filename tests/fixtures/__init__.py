"""Test fixture helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

_FIXTURE_ROOT = Path(__file__).parent


def load_json(name: str) -> dict[str, Any]:
    """Load a JSON fixture by filename."""

    data = json.loads((_FIXTURE_ROOT / name).read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Fixture '{name}' does not contain a JSON object.")
    return cast(dict[str, Any], data)
