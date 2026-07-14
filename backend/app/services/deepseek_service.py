import json
from typing import Any

import requests
from loguru import logger

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.settings import DataSourceConfig


class DeepSeekClientError(RuntimeError):
    pass


def deepseek_configured() -> bool:
    api_key, _ = get_deepseek_runtime_config()
    return bool(api_key)


def complete_json(*, system_prompt: str, user_prompt: str) -> dict[str, Any]:
    settings = get_settings()
    api_key, base_url = get_deepseek_runtime_config()
    if not api_key:
        raise DeepSeekClientError("DEEPSEEK_API_KEY is not configured")
    payload: dict[str, Any] = {
        "model": settings.deepseek_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "max_tokens": settings.deepseek_max_tokens,
        "response_format": {"type": "json_object"},
        "thinking": {"type": "enabled" if settings.deepseek_thinking_enabled else "disabled"},
    }
    if settings.deepseek_thinking_enabled:
        payload["reasoning_effort"] = "high"
    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=settings.deepseek_timeout_seconds,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError) as exc:
        logger.warning("DeepSeek completion failed: {}", exc)
        raise DeepSeekClientError(str(exc)) from exc


def get_deepseek_runtime_config() -> tuple[str | None, str]:
    settings = get_settings()
    api_key = settings.deepseek_api_key
    base_url = settings.deepseek_base_url
    try:
        with SessionLocal() as db:
            row = db.query(DataSourceConfig).filter(DataSourceConfig.provider_code == "deepseek").first()
            if row and not row.enabled:
                return None, row.base_url or base_url
            if row:
                api_key = row.secret_value or api_key
                base_url = row.base_url or base_url
    except Exception:
        return api_key, base_url
    return api_key, base_url
