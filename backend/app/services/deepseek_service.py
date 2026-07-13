import json
from typing import Any

import requests
from loguru import logger

from app.core.config import get_settings


class DeepSeekClientError(RuntimeError):
    pass


def deepseek_configured() -> bool:
    return bool(get_settings().deepseek_api_key)


def complete_json(*, system_prompt: str, user_prompt: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.deepseek_api_key:
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
            f"{settings.deepseek_base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.deepseek_api_key}",
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
