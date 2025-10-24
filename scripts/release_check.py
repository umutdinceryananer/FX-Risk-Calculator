#!/usr/bin/env python
"""Release readiness check.

Runs linting, type checks, backend tests, and performs a quick health endpoint smoke test.
Intended for local use prior to tagging a release.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from typing import Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]

COMMANDS: Sequence[Tuple[str, Sequence[str]]] = (
    ("Lint", ("make", "lint")),
    ("Type check", ("make", "typecheck")),
    ("Backend tests", ("make", "test")),
)


def run_command(label: str, command: Sequence[str]) -> None:
    print(f"[RUN] {label}: {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def health_smoke_test() -> None:
    print("[RUN] Health check: /health & /health/rates", flush=True)
    sys.path.insert(0, str(REPO_ROOT))
    from app import create_app

    app = create_app("development")
    with app.app_context():
        with app.test_client() as client:
            for endpoint in ("/health", "/health/rates"):
                response = client.get(endpoint)
                if response.status_code != 200:
                    raise RuntimeError(f"{endpoint} returned {response.status_code}")


def main() -> int:
    try:
        for label, command in COMMANDS:
            run_command(label, command)
        health_smoke_test()
    except subprocess.CalledProcessError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return exc.returncode or 1
    except Exception as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    print("[OK] Release check succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
