from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import requests

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.settings import DataSourceConfig

PERMISSION_DENIED_CODE = -2002


def tushare_query(
    api_name: str,
    *,
    params: dict[str, Any] | None = None,
    fields: list[str] | None = None,
) -> pd.DataFrame:
    token, api_url = get_tushare_runtime_config()
    if not token:
        raise RuntimeError("Tushare token is not configured")

    response = requests.post(
        api_url,
        json={
            "api_name": api_name,
            "token": token,
            "params": params or {},
            "fields": ",".join(fields) if fields else "",
        },
        timeout=20,
        headers={"Content-Type": "application/json"},
    )
    response.raise_for_status()
    payload = response.json()

    code = payload.get("code", 0)
    if code == PERMISSION_DENIED_CODE:
        raise RuntimeError(f"Tushare permission denied for {api_name}: {payload.get('msg') or 'insufficient points'}")
    if code not in (0, None):
        raise RuntimeError(f"Tushare request failed for {api_name}: {payload.get('msg') or code}")

    data = payload.get("data") or {}
    items = data.get("items") or []
    columns = data.get("fields") or fields or []
    if not items:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(items, columns=columns)


def get_tushare_runtime_config() -> tuple[str | None, str]:
    settings = get_settings()
    token = settings.tushare_token
    api_url = settings.tushare_api_url
    try:
        with SessionLocal() as db:
            row = db.query(DataSourceConfig).filter(DataSourceConfig.provider_code == "tushare").first()
            if row and not row.enabled:
                return None, row.base_url or api_url
            if row:
                token = row.secret_value or token
                api_url = row.base_url or api_url
    except Exception:
        return token, api_url
    return token, api_url


def fetch_trade_calendar(start_date: date, end_date: date, exchange: str = "SSE") -> pd.DataFrame:
    return tushare_query(
        "trade_cal",
        params={
            "exchange": exchange,
            "start_date": start_date.strftime("%Y%m%d"),
            "end_date": end_date.strftime("%Y%m%d"),
        },
        fields=["exchange", "cal_date", "is_open", "pretrade_date"],
    )


def fetch_fund_daily(ts_code: str, start_date: date, end_date: date) -> pd.DataFrame:
    return tushare_query(
        "fund_daily",
        params={
            "ts_code": ts_code,
            "start_date": start_date.strftime("%Y%m%d"),
            "end_date": end_date.strftime("%Y%m%d"),
        },
        fields=["ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"],
    )


def fetch_fund_nav(ts_code: str) -> pd.DataFrame:
    return tushare_query(
        "fund_nav",
        params={"ts_code": ts_code},
        fields=["ts_code", "ann_date", "end_date", "unit_nav", "accum_nav", "net_asset", "total_netasset", "adj_nav"],
    )


def fetch_fund_share(ts_code: str) -> pd.DataFrame:
    return tushare_query(
        "fund_share",
        params={"ts_code": ts_code},
        fields=["ts_code", "trade_date", "fd_share"],
    )


def fetch_index_daily(ts_code: str, start_date: date, end_date: date) -> pd.DataFrame:
    return tushare_query(
        "index_daily",
        params={
            "ts_code": ts_code,
            "start_date": start_date.strftime("%Y%m%d"),
            "end_date": end_date.strftime("%Y%m%d"),
        },
        fields=["ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"],
    )


def fetch_fund_basic(*, market: str = "E", status: str = "L") -> pd.DataFrame:
    return tushare_query(
        "fund_basic",
        params={"market": market, "status": status},
        fields=[
            "ts_code",
            "name",
            "management",
            "custodian",
            "fund_type",
            "found_date",
            "list_date",
            "delist_date",
            "issue_amount",
            "m_fee",
            "c_fee",
            "benchmark",
            "status",
            "market",
        ],
    )


def to_tushare_code(symbol: str, exchange: str | None = None) -> str:
    normalized_exchange = (exchange or "").strip().upper()
    if normalized_exchange in {"SH", "SSE", "XSHG"}:
        suffix = "SH"
    elif normalized_exchange in {"SZ", "SZSE", "XSHE"}:
        suffix = "SZ"
    elif symbol.startswith(("5", "6", "9")):
        suffix = "SH"
    else:
        suffix = "SZ"
    return f"{symbol}.{suffix}"
