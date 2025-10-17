"""Blueprint scaffolding for portfolio position management."""

from __future__ import annotations

from flask_smorest import Blueprint

blp = Blueprint("Positions", __name__, description="Portfolio position endpoints")

from . import routes  # noqa: E402,F401
