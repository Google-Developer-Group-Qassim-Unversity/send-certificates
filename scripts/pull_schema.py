#!/usr/bin/env python3
"""
Pull database schema and generate SQLModel classes.

Usage:
    python scripts/pull_schema.py

This will introspect the database and generate app/db/schema.py
"""

import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in .env file")
    sys.exit(1)

if DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)

SCHEMA_OUTPUT_PATH = Path("app/db/schema.py")


def main():
    print("Pulling schema from database...")
    print(f"Output: {SCHEMA_OUTPUT_PATH}")

    cmd = [
        "sqlacodegen",
        "--generator",
        "sqlmodels",
        "--outfile",
        str(SCHEMA_OUTPUT_PATH),
        DATABASE_URL,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("ERROR: sqlacodegen-sqlmodel failed")
        print(result.stderr)
        sys.exit(1)

    print("Schema pulled successfully!")
    print(f"\nGenerated file: {SCHEMA_OUTPUT_PATH}")

    with open(SCHEMA_OUTPUT_PATH, "r") as f:
        content = f.read()

    print(f"\n--- Preview of {SCHEMA_OUTPUT_PATH} ---")
    lines = content.split("\n")
    preview_lines = lines[:50]
    print("\n".join(preview_lines))
    if len(lines) > 50:
        print(f"\n... ({len(lines) - 50} more lines)")


if __name__ == "__main__":
    main()
