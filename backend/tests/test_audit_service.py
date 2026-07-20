from app.services.audit_service import resolve_action


def test_resolve_action_from_api_path() -> None:
    assert resolve_action("POST", "/api/market/sync") == "post_market"
    assert resolve_action("PATCH", "/api/data-sources/tushare") == "patch_data_sources"
