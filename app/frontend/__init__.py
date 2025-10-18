"""Blueprint serving the SPA frontend assets."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, abort, send_from_directory

FRONTEND_ROOT = (Path(__file__).resolve().parents[2] / "frontend").resolve()

blp = Blueprint("frontend", __name__, url_prefix="/app")


@blp.route("/", defaults={"resource_path": "index.html"})
@blp.route("/<path:resource_path>")
def serve_frontend(resource_path: str):
    """Serve compiled frontend assets or fallback to index.html for SPA routing."""

    requested_path = (FRONTEND_ROOT / resource_path).resolve()

    # Prevent directory traversal outside the frontend root
    if not str(requested_path).startswith(str(FRONTEND_ROOT)):
        abort(404)

    if not requested_path.exists() or requested_path.is_dir():
        return send_from_directory(FRONTEND_ROOT, "index.html")

    relative_path = requested_path.relative_to(FRONTEND_ROOT)
    return send_from_directory(FRONTEND_ROOT, str(relative_path))
