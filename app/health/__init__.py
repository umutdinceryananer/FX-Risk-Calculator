"""Health blueprint module."""

from __future__ import annotations

from flask_smorest import Blueprint

blp = Blueprint("Health", __name__, description="Service health endpoints")

from . import routes  # noqa: E402,F401
