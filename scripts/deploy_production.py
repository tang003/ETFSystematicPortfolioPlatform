from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from validate_production_env import load_env_file, validate


def run(command: list[str], *, allow_failure: bool = False) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(command))
    result = subprocess.run(command, text=True)
    if result.returncode and not allow_failure:
        raise subprocess.CalledProcessError(result.returncode, command)
    return result


def compose_prefix(compose_file: str, env_file: str) -> list[str]:
    return ["docker", "compose", "--env-file", env_file, "-f", compose_file]


def service_exists(prefix: list[str], service: str) -> bool:
    result = subprocess.run([*prefix, "ps", "-q", service], capture_output=True, text=True)
    return result.returncode == 0 and bool(result.stdout.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy the ETF platform on a production server.")
    parser.add_argument("--compose-file", default="compose.production.yml")
    parser.add_argument("--env-file", default=".env.production")
    parser.add_argument("--skip-backup", action="store_true")
    parser.add_argument("--skip-pull", action="store_true")
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

    prefix = compose_prefix(args.compose_file, args.env_file)

    try:
        if not args.skip_pull:
            run(["git", "pull", "--ff-only"])

        if not args.skip_backup and service_exists(prefix, "postgres"):
            run(
                [
                    sys.executable,
                    "scripts/backup_database.py",
                    "--compose-file",
                    args.compose_file,
                    "--env-file",
                    args.env_file,
                ]
            )
        elif args.skip_backup:
            print("backup skipped by request")
        else:
            print("postgres service is not running yet; backup skipped for first deployment")

        run([*prefix, "config", "-q"])
        run([*prefix, "up", "-d", "--build"])
        run([*prefix, "ps"])
        run(
            [
                *prefix,
                "exec",
                "-T",
                "api",
                "python",
                "-c",
                (
                    "import requests; "
                    "requests.get('http://127.0.0.1:8000/health/ready', "
                    "headers={'Host':'localhost'}, timeout=10).raise_for_status(); "
                    "print('api ready')"
                ),
            ]
        )
    except subprocess.CalledProcessError as exc:
        print(f"deploy failed at command: {' '.join(exc.cmd)}", file=sys.stderr)
        run([*prefix, "logs", "--tail=120", "api"], allow_failure=True)
        run([*prefix, "logs", "--tail=120", "worker"], allow_failure=True)
        return exc.returncode or 1

    print("production deploy completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
