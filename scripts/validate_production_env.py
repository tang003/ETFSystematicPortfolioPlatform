from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_KEYS = [
    "DOMAIN",
    "ACME_EMAIL",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "AUTH_ENABLED",
    "AUTH_ADMIN_USERNAME",
    "AUTH_ADMIN_PASSWORD_HASH",
    "AUTH_SESSION_SECRET",
    "AUTH_COOKIE_SECURE",
    "WORKFLOW_EXECUTION_MODE",
]


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def validate(values: dict[str, str]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for key in REQUIRED_KEYS:
        if not values.get(key):
            errors.append(f"{key} is required")

    domain = values.get("DOMAIN", "")
    if domain in {"etf.example.com", "localhost", "127.0.0.1"} or "." not in domain:
        errors.append("DOMAIN must be a real domain already pointed to the server")

    email = values.get("ACME_EMAIL", "")
    if email == "admin@example.com" or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        errors.append("ACME_EMAIL must be a real certificate notification email")

    postgres_password = values.get("POSTGRES_PASSWORD", "")
    if postgres_password in {"quant_etf_password", "replace-with-a-long-random-password"}:
        errors.append("POSTGRES_PASSWORD must not use a default or placeholder value")
    if len(postgres_password) < 16:
        errors.append("POSTGRES_PASSWORD should contain at least 16 characters")

    if values.get("AUTH_ENABLED", "").lower() != "true":
        errors.append("AUTH_ENABLED must be true")
    if values.get("AUTH_COOKIE_SECURE", "").lower() != "true":
        errors.append("AUTH_COOKIE_SECURE must be true")

    password_hash = values.get("AUTH_ADMIN_PASSWORD_HASH", "")
    if not password_hash.startswith("pbkdf2_sha256$") or "replace-with-" in password_hash:
        errors.append("AUTH_ADMIN_PASSWORD_HASH must come from scripts/generate_auth_secrets.py")

    session_secret = values.get("AUTH_SESSION_SECRET", "")
    if len(session_secret) < 32 or "replace-with-" in session_secret:
        errors.append("AUTH_SESSION_SECRET must contain at least 32 non-placeholder characters")

    if values.get("WORKFLOW_EXECUTION_MODE") != "worker":
        errors.append("WORKFLOW_EXECUTION_MODE must be worker on the production server")

    interval = values.get("TUSHARE_REQUEST_INTERVAL_SECONDS")
    if interval:
        try:
            if float(interval) < 1.5:
                warnings.append("TUSHARE_REQUEST_INTERVAL_SECONDS is below 1.5; shared tokens may be rate limited")
        except ValueError:
            errors.append("TUSHARE_REQUEST_INTERVAL_SECONDS must be a number")

    if not values.get("TUSHARE_TOKEN"):
        warnings.append("TUSHARE_TOKEN is empty; real Tushare data will not be available")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate production environment settings without printing secrets.")
    parser.add_argument("--env-file", default=".env.production")
    args = parser.parse_args()

    env_path = Path(args.env_file)
    if not env_path.exists():
        print(f"env file not found: {env_path}", file=sys.stderr)
        return 1

    errors, warnings = validate(load_env_file(env_path))
    for warning in warnings:
        print(f"warning: {warning}")
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"production env looks ready: {env_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
