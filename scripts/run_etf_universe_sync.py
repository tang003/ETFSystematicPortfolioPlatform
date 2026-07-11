import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.database import SessionLocal  # noqa: E402
from app.services.asset_service import sync_etf_universe  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync full-market ETF universe into asset_master.")
    parser.add_argument("--source", default="akshare", choices=["akshare"])
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    with SessionLocal() as db:
        result = sync_etf_universe(db, source=args.source, limit=args.limit)
    print(
        f"source={result['source']} total={result['total']} "
        f"inserted_or_updated={result['inserted_or_updated']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
