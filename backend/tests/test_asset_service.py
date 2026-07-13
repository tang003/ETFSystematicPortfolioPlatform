from decimal import Decimal

from app.schemas.asset_schema import AssetUpsertItem
from app.services import asset_service


def test_build_asset_item_from_market_row_maps_cn_etf() -> None:
    item = asset_service.build_asset_item_from_market_row({"代码": "159928", "名称": "消费ETF"})

    assert item is not None
    assert item.symbol == "159928"
    assert item.name == "消费ETF"
    assert item.exchange == "SZ"
    assert item.asset_class == "equity"
    assert item.asset_region == "CN"
    assert item.enabled is False


def test_classify_cross_border_etf() -> None:
    meta = asset_service.classify_etf_asset("513050", "中概互联网ETF")

    assert meta["asset_class"] == "qdii"
    assert meta["asset_region"] == "CN_HK_US"
    assert meta["is_cross_border"] is True
    assert meta["risk_level"] == 5


def test_classify_bond_and_gold_etf() -> None:
    assert asset_service.classify_etf_asset("511010", "国债ETF")["asset_class"] == "bond"
    assert asset_service.classify_etf_asset("518880", "黄金ETF")["asset_class"] == "gold"


def test_normalize_symbol_handles_numeric_like_values() -> None:
    assert asset_service.normalize_symbol("159928.0") == "159928"
    assert asset_service.normalize_symbol(928) == "000928"
    assert asset_service.normalize_symbol("ABC") is None


def test_asset_upsert_item_accepts_profile_fields() -> None:
    item = AssetUpsertItem(
        symbol="510300",
        name="沪深300ETF",
        fund_company="华泰柏瑞基金",
        tracking_index="沪深300",
        fund_size=Decimal("10000000000"),
        management_fee=Decimal("0.005"),
        custody_fee=Decimal("0.001"),
    )

    assert item.tracking_index == "沪深300"
    assert item.fund_size == Decimal("10000000000")
