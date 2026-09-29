"""The sole production long-term memory implementation: Hindsight Cloud."""
import logging
from typing import Protocol
from app.config import settings
from app.domain.models import MemoryUsed

logger = logging.getLogger(__name__)


class MemoryUnavailable(RuntimeError):
    pass


def _is_missing_bank(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    if status == 404:
        return True
    return "not found" in str(exc).lower()


class MemoryGateway(Protocol):
    async def retain(self, content: str, *, context: str, document_id: str, metadata: dict[str, str]) -> None: ...
    async def recall(self, query: str, limit: int = 8) -> list[MemoryUsed]: ...


class HindsightGateway:
    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if not settings.hindsight_api_key:
            raise MemoryUnavailable("Memory service unavailable. Configure HINDSIGHT_API_KEY to enable Hindsight.")
        if self._client is None:
            try:
                from hindsight_client import Hindsight
                self._client = Hindsight(base_url=settings.hindsight_base_url, api_key=settings.hindsight_api_key)
            except Exception as exc:
                logger.error("Failed to construct Hindsight client: %s", exc)
                raise MemoryUnavailable("Memory service unavailable.") from exc
        return self._client

    async def _ensure_bank(self) -> None:
        """Create the memory bank on first use so recall/retain never hit a 404."""
        client = self._get_client()
        try:
            await client.aget_bank_config(bank_id=settings.hindsight_bank_id)
        except Exception as exc:
            if not _is_missing_bank(exc):
                logger.warning("Hindsight bank probe failed (will still attempt create): %s", exc)
            try:
                await client.acreate_bank(
                    bank_id=settings.hindsight_bank_id,
                    name="Echo Chamber",
                    mission="Retain product decisions, debate outcomes, and validated lessons so future recommendations improve.",
                )
                logger.info("Created Hindsight bank '%s'", settings.hindsight_bank_id)
            except Exception as create_exc:
                if _is_missing_bank(create_exc) or "already exists" in str(create_exc).lower():
                    return
                logger.error("Failed to create Hindsight bank '%s': %s", settings.hindsight_bank_id, create_exc)
                raise MemoryUnavailable("Memory service unavailable.") from create_exc

    async def retain(self, content: str, *, context: str, document_id: str, metadata: dict[str, str]) -> None:
        try:
            await self._get_client().aretain(
                bank_id=settings.hindsight_bank_id, content=content, context=context,
                document_id=document_id, metadata=metadata,
            )
        except MemoryUnavailable:
            raise
        except Exception as exc:
            if _is_missing_bank(exc):
                await self._ensure_bank()
                return await self.retain(content, context=context, document_id=document_id, metadata=metadata)
            logger.error("Hindsight retain failed: %s", exc)
            raise MemoryUnavailable("Memory service unavailable.") from exc

    async def recall(self, query: str, limit: int = 8) -> list[MemoryUsed]:
        try:
            await self._ensure_bank()
            response = await self._get_client().arecall(
                bank_id=settings.hindsight_bank_id, query=query, max_tokens=1200
            )
            results = getattr(response, "results", [])[:limit]
            return [MemoryUsed(
                id=str(getattr(item, "id", index)), kind=str(getattr(item, "type", "memory")),
                text=str(getattr(item, "text", "")), impact="Historical context was included in this evaluation.",
                source_decision_id=(getattr(item, "metadata", {}) or {}).get("decision_id"),
            ) for index, item in enumerate(results)]
        except MemoryUnavailable:
            raise
        except Exception as exc:
            logger.error("Hindsight recall failed: %s", exc)
            raise MemoryUnavailable("Memory service unavailable.") from exc
