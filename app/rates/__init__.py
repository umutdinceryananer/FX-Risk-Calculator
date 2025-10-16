from __future__ import annotations

from flask import Blueprint

bp = Blueprint("rates", __name__)

from . import routes  # noqa: E402,F401

