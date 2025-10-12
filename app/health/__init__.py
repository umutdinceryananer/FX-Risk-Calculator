"""Health blueprint module."""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint("health", __name__)

# Import routes to ensure they are registered with the blueprint.
from . import routes  # noqa: E402,F401
