"""Blueprint scaffolding for portfolio management endpoints."""

from __future__ import annotations

from flask_smorest import Blueprint

blp = Blueprint("Portfolios", __name__, description="Portfolio management endpoints")

from . import routes  # noqa: E402,F401
