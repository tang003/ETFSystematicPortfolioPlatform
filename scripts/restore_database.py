from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path


def run_command(command: list[str], *, stdout=None, stdin=None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, check=True, stdout=stdout, stdin=stdin)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def docker_compose_prefix(compose_file: str, env_file: str) -> list[str]:
    command = ["docker", "compose"]
    if compose_file:
        command.extend(["-f", compose_file])
    if env_file:
        command.extend(["--env-file", env_file])
    return command


def read_container_database(prefix: list[str], service: str) -> str:
    result = subprocess.run(
        [*prefix, "exec", "-T", service, "printenv", "POSTGRES_DB"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def verify_checksum(backup_path: Path) -> None:
    checksum_path = backup_path.with_suffix(backup_path.suffix + ".sha256")
    if not checksum_path.exists():
        raise RuntimeError(f"checksum file is missing: {checksum_path}")
    expected = checksum_path.read_text(encoding="utf-8").split()[0]
    actual = sha256_file(backup_path)
    if actual != expected:
        raise RuntimeError("backup checksum mismatch")


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore a verified PostgreSQL backup into the compose database.")
    parser.add_argument("backup", help="Path to the .dump backup file.")
    parser.add_argument("--compose-file", default="compose.production.yml")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--postgres-service", default="postgres")
    parser.add_argument("--api-service", default="api")
    parser.add_argument("--database", default=os.getenv("POSTGRES_DB", "quant_etf"))
    parser.add_argument("--user", default=os.getenv("POSTGRES_USER", "quant_etf"))
    parser.add_argument("--confirm-database", required=True)
    args = parser.parse_args()

    backup_path = Path(args.backup)
    if not backup_path.exists():
        print(f"backup file not found: {backup_path}", file=sys.stderr)
        return 1

    prefix = docker_compose_prefix(args.compose_file, args.env_file)

    try:
        actual_database = read_container_database(prefix, args.postgres_service)
        if args.confirm_database != actual_database:
            raise RuntimeError(
                f"--confirm-database must equal the running database name: {actual_database}"
            )
        if args.database != actual_database:
            raise RuntimeError(f"--database must equal the running database name: {actual_database}")

        verify_checksum(backup_path)
        with backup_path.open("rb") as file:
            run_command(
                ["docker", "run", "--rm", "-i", "postgres:16-alpine", "pg_restore", "--list"],
                stdin=file,
                stdout=subprocess.DEVNULL,
            )

        run_command([*prefix, "stop", args.api_service])
        try:
            with backup_path.open("rb") as file:
                run_command(
                    [
                        *prefix,
                        "exec",
                        "-T",
                        args.postgres_service,
                        "pg_restore",
                        "-U",
                        args.user,
                        "-d",
                        args.database,
                        "--clean",
                        "--if-exists",
                        "--no-owner",
                    ],
                    stdin=file,
                )
        finally:
            run_command([*prefix, "up", "-d", args.api_service])
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"restore failed: {exc}", file=sys.stderr)
        return 1

    print(f"restore completed: {backup_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
