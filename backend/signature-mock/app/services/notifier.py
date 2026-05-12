"""Sends the completion webhook to the agent after all signatures are collected."""
from __future__ import annotations

import asyncio

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()


async def notify_agent(
    *,
    envelope_id: str,
    contract_id: str,
    callback_url: str | None,
    signers: list[dict],
) -> None:
    url = callback_url or settings.agent_callback_url
    payload = {
        "envelope_id": envelope_id,
        "contract_id": contract_id,
        "status": "completed",
        "signers": signers,
    }
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
            logger.info("webhook_sent", envelope_id=envelope_id, url=url)
            return
        except Exception as exc:
            logger.warning("webhook_attempt_failed", attempt=attempt + 1, error=str(exc))
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)

    logger.error("webhook_all_attempts_failed", envelope_id=envelope_id)
