from app.services.audit_service import resolve_action, sanitize_query_params


def test_resolve_action_from_api_path() -> None:
    assert resolve_action("POST", "/api/market/sync") == "post_market"
    assert resolve_action("PATCH", "/api/data-sources/tushare") == "patch_data_sources"


def test_sanitize_query_params_masks_sensitive_values() -> None:
    assert sanitize_query_params(
        {
            "symbol": "510300",
            "token": "secret-token",
            "api_key": "secret-key",
            "clientSecret": "secret-value",
        }
    ) == {
        "symbol": "510300",
        "token": "***",
        "api_key": "***",
        "clientSecret": "***",
    }
