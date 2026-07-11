"""Run an incremental market sync for the platform's core ETF universe.

This script is designed for server cron/systemd timers. It does not place
orders and only updates local market-data tables.
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.database import SessionLocal  # noqa: E402
from app.services.market_service import sync_market_data  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync core ETF market data.")
    parser.add_argument("--source", default="tushare", choices=["tushare", "akshare", "eastmoney"])
    parser.add_argument("--scope", default="core", choices=["core", "positions", "target", "plans", "enabled", "all"])
    parser.add_argument("--days", type=int, default=45, help="Lookback days for first fill or repair.")
    parser.add_argument("--max-symbols", type=int, default=30)
    parser.add_argument("--interval", type=float, default=1.5)
    parser.add_argument("--full", action="store_true", help="Disable incremental mode.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    end_date = date.today()
    start_date = end_date - timedelta(days=max(args.days, 1))
    db = SessionLocal()
    try:
        result = sync_market_data(
            db,
            symbols=None,
            sync_scope=args.scope,
            start_date=start_date,
            end_date=end_date,
            source=args.source,
            incremental=not args.full,
            clean_after_sync=True,
            max_symbols=args.max_symbols,
            request_interval_seconds=args.interval,
        )
    finally:
        db.close()

    print(
        "market sync completed: "
        f"scope={result['sync_scope']} source={result['source']} "
        f"success={result['success_count']} failed={result['failed_count']} "
        f"clean_rows={result['total_clean_rows']}"
    )
    return 1 if result["failed_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
