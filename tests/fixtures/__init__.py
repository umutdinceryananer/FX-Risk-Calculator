"""Test fixture helpers."""

from __future__ import annotations

import json
from pathlib import Path

_FIXTURE_ROOT = Path(__file__).parent


def load_json(name: str) -> dict:
    """Load a JSON fixture by filename."""

    return json.loads((_FIXTURE_ROOT / name).read_text())
