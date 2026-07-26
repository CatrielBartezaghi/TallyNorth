"""Run production-safe preparation for the Vercel FastAPI service."""

import os
import subprocess
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    if os.getenv("VERCEL_ENV") != "production":
        print("Skipping database migrations outside Vercel production.")
        return

    if not os.getenv("DATABASE_URL"):
        raise RuntimeError(
            "DATABASE_URL is required for production database migrations"
        )

    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_ROOT,
        check=True,
    )
    print("Production database migrations are at Alembic head.")


if __name__ == "__main__":
    main()
