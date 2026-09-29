"""Small OpenAI-compatible JSON client for configurable providers such as TokenRouter."""
import json
import logging
from typing import Any
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class OpenAICompatibleLLM:
    async def complete_json(self, *, system: str, user: str) -> dict[str, Any] | None:
        if not settings.llm_api_key:
            logger.warning("LLM_API_KEY is not configured; using structured fallback.")
            return None
        base_url = settings.llm_base_url.rstrip("/")
        endpoint = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"
        payload = {
            "model": settings.llm_model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_object"},
            "temperature": 0.25,
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=8.0)) as client:
                response = await client.post(endpoint, headers={"Authorization": f"Bearer {settings.llm_api_key}"}, json=payload)
                if response.status_code >= 400:
                    logger.warning("LLM provider returned %s: %s", response.status_code, response.text[:300])
                    response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except (httpx.HTTPError, KeyError, TypeError, IndexError, json.JSONDecodeError) as exc:
            logger.warning("LLM analysis unavailable; using structured fallback: %s", type(exc).__name__)
            return None
