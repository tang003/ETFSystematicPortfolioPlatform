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


def test_infer_profile_from_etf_name() -> None:
    assert asset_service.infer_fund_company("华夏上证50ETF") == "华夏基金"
    assert asset_service.infer_tracking_index("华夏上证50ETF") == "上证50"
    assert asset_service.infer_tracking_index("纳指ETF") == "纳斯达克100"


def test_build_profile_patch_parses_market_row() -> None:
    patch = asset_service.build_profile_patch(
        "510300",
        "沪深300ETF",
        {
            "名称": "华泰柏瑞沪深300ETF",
            "基金规模": "890.25亿",
            "管理费率": "0.50%",
            "托管费率": "0.10%",
            "溢价率": "-0.02%",
        },
    )

    assert patch["name"] == "华泰柏瑞沪深300ETF"
    assert patch["fund_company"] == "华泰柏瑞基金"
    assert patch["tracking_index"] == "沪深300"
    assert patch["fund_size"] == Decimal("89025000000.00")
    assert patch["management_fee"] == Decimal("0.0050")
    assert patch["custody_fee"] == Decimal("0.0010")
    assert patch["expense_ratio"] == Decimal("0.0060")
    assert patch["latest_premium_rate"] == Decimal("-0.0002")


def test_write_asset_sync_log_marks_partial_status() -> None:
    class Db:
        def __init__(self) -> None:
            self.rows = []

        def add(self, row) -> None:
            self.rows.append(row)

    db = Db()

    asset_service.write_asset_sync_log(
        db,
        sync_type="profile",
        result={"source": "akshare", "total": 3, "updated": 2, "skipped": 0, "failed": 1, "results": []},
        message="done",
    )

    assert db.rows[0].status == "partial"
    assert db.rows[0].updated == 2


def test_fetch_etf_universe_falls_back_to_eastmoney(monkeypatch) -> None:
    monkeypatch.setattr(asset_service, "fetch_akshare_etf_universe", lambda limit=None: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(
        asset_service,
        "fetch_eastmoney_etf_rows",
        lambda limit=None: [{"代码": "510300", "名称": "沪深300ETF"}],
    )

    items, source = asset_service.fetch_etf_universe(source="auto")

    assert source == "eastmoney"
    assert items[0].symbol == "510300"


def test_fetch_etf_universe_auto_prefers_eastmoney(monkeypatch) -> None:
    called = {"akshare": False}

    def fail_akshare(limit=None):
        called["akshare"] = True
        raise RuntimeError("should not call akshare first")

    monkeypatch.setattr(asset_service, "fetch_akshare_etf_universe", fail_akshare)
    monkeypatch.setattr(
        asset_service,
        "fetch_eastmoney_etf_rows",
        lambda limit=None: [{"代码": "510300", "名称": "沪深300ETF"}],
    )

    items, source = asset_service.fetch_etf_universe(source="auto")

    assert source == "eastmoney"
    assert items[0].symbol == "510300"
    assert called["akshare"] is False


def test_fetch_etf_universe_falls_back_to_tushare_before_akshare(monkeypatch) -> None:
    called = {"akshare": False}

    class Frame:
        def to_dict(self, orient):
            assert orient == "records"
            return [{"ts_code": "510300.SH", "name": "沪深300ETF", "management": "华泰柏瑞基金"}]

    monkeypatch.setattr(asset_service, "fetch_eastmoney_etf_universe", lambda limit=None: (_ for _ in ()).throw(RuntimeError("eastmoney down")))
    monkeypatch.setattr(asset_service, "fetch_fund_basic", lambda market="E", status="L": Frame())
    monkeypatch.setattr(asset_service, "fetch_akshare_etf_universe", lambda limit=None: called.__setitem__("akshare", True))

    items, source = asset_service.fetch_etf_universe(source="auto")

    assert source == "tushare"
    assert items[0].symbol == "510300"
    assert called["akshare"] is False


def test_build_asset_item_from_tushare_row_maps_fees_and_profile() -> None:
    item = asset_service.build_asset_item_from_tushare_row(
        {
            "ts_code": "159928.SZ",
            "name": "消费ETF",
            "management": "汇添富基金",
            "benchmark": "中证主要消费指数",
            "m_fee": "0.50",
            "c_fee": "0.10",
            "list_date": "20130823",
        }
    )

    assert item is not None
    assert item.symbol == "159928"
    assert item.exchange == "SZ"
    assert item.fund_company == "汇添富基金"
    assert item.tracking_index == "中证主要消费指数"
    assert item.management_fee == Decimal("0.0050")
    assert item.custody_fee == Decimal("0.0010")
    assert item.expense_ratio == Decimal("0.0060")


def test_friendly_external_error_translates_remote_disconnect() -> None:
    message = asset_service.friendly_external_error(RuntimeError("RemoteDisconnected without response"))

    assert "外部 ETF 列表接口主动断开连接" in message
