"""Entry point for running the FX Risk Calculator Flask app."""

from __future__ import annotations

import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None

from app import create_app


def _prepare_environment() -> None:
    """Load environment variables from a local .env file if available."""

    if load_dotenv is None:
        return

    # Load `.env` in the repository root when python-dotenv is available.
    project_root = os.path.abspath(os.path.dirname(__file__))
    env_file = os.path.join(project_root, ".env")
    if os.path.exists(env_file):
        load_dotenv(env_file)


def main() -> None:
    """Create the Flask app and run the development server."""

    _prepare_environment()

    config_name = os.getenv("APP_ENV")
    app = create_app(config_name=config_name)

    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", "5000"))
    debug = app.config.get("DEBUG", False)

    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
