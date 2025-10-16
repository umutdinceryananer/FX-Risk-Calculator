"""Currencies blueprint providing validation endpoints."""

from __future__ import annotations

from flask_smorest import Blueprint

blp = Blueprint("Currencies", __name__, description="Currency validation endpoints")

from . import routes  # noqa: E402,F401
