from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def run_command(command: list[str], *, stdout=None, stdin=None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, check=True, stdout=stdout, stdin=stdin)


def remove_expired_backups(output_dir: Path, retention_days: int) -> None:
    if retention_days <= 0:
        return
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    for path in output_dir.glob("*.dump"):
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if modified >= cutoff:
            continue
        path.unlink(missing_ok=True)
        path.with_suffix(path.suffix + ".sha256").unlink(missing_ok=True)


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a verified PostgreSQL backup from the compose database.")
    parser.add_argument("--compose-file", default="compose.production.yml")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--service", default="postgres")
    parser.add_argument("--database", default=os.getenv("POSTGRES_DB", "quant_etf"))
    parser.add_argument("--user", default=os.getenv("POSTGRES_USER", "quant_etf"))
    parser.add_argument("--output-dir", default="backups")
    parser.add_argument("--retention-days", type=int, default=30)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = output_dir / f"{args.database}_{timestamp}.dump"
    checksum_path = backup_path.with_suffix(backup_path.suffix + ".sha256")

    prefix = docker_compose_prefix(args.compose_file, args.env_file)
    dump_command = [
        *prefix,
        "exec",
        "-T",
        args.service,
        "pg_dump",
        "-U",
        args.user,
        "-d",
        args.database,
        "-F",
        "c",
        "--no-owner",
        "--no-privileges",
    ]

    try:
        with backup_path.open("wb") as file:
            run_command(dump_command, stdout=file)
        digest = sha256_file(backup_path)
        checksum_path.write_text(f"{digest}  {backup_path.name}\n", encoding="utf-8")

        with backup_path.open("rb") as file:
            run_command(
                ["docker", "run", "--rm", "-i", "postgres:16-alpine", "pg_restore", "--list"],
                stdin=file,
                stdout=subprocess.DEVNULL,
            )

        remove_expired_backups(output_dir, args.retention_days)
    except subprocess.CalledProcessError as exc:
        backup_path.unlink(missing_ok=True)
        checksum_path.unlink(missing_ok=True)
        print(f"backup failed: {exc}", file=sys.stderr)
        return 1

    print(f"backup created: {backup_path}")
    print(f"sha256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
