"""Node 8 — compute chained seal and archive the contract."""
import asyncio
import hashlib
import json
import time
from datetime import datetime, timezone

import structlog

from app.config import settings
from app.schemas.state import ContractState
from app.services import db as db_svc
from app.services.storage import download_file, upload_file

logger = structlog.get_logger()


def _compute_seal(document_hash: str, previous_seal: str | None, timestamp: str) -> str:
    payload = f"{document_hash}{previous_seal or ''}{timestamp}"
    return hashlib.sha256(payload.encode()).hexdigest()


async def archive(state: ContractState) -> dict:
    contract_id = state["contract_id"]
    step_id = await db_svc.create_agent_step(contract_id, "archive")
    t0 = time.monotonic()

    try:
        info = await db_svc.get_contract_minio_info(contract_id)
        if not info:
            raise ValueError("Contract not found")
        bucket, key = info
        loop = asyncio.get_event_loop()
        document_bytes = await loop.run_in_executor(None, download_file, bucket, key)

        document_hash = hashlib.sha256(document_bytes).hexdigest()
        previous_seal = await db_svc.get_latest_seal_hash()
        ts = datetime.now(timezone.utc).isoformat()
        seal_hash = _compute_seal(document_hash, previous_seal, ts)

        receipt: dict = {
            "contract_id": contract_id,
            "original_filename": key.split("/")[-1],
            "document_hash_sha256": document_hash,
            "seal_hash": seal_hash,
            "previous_seal_hash": previous_seal,
            "archive_timestamp": ts,
            "signers": [
                {
                    "name": s.get("name"),
                    "email": s.get("email"),
                    "signed_at": s.get("signed_at"),
                    "verification_valid": s.get("verification_valid"),
                }
                for s in state.get("signatures_data", [])
            ],
            "contract_type": state.get("contract_type"),
            "risk_level": state.get("risk_level"),
        }

        archive_key = f"{contract_id}/archive-receipt.json"
        receipt_bytes = json.dumps(receipt, ensure_ascii=False, indent=2).encode()
        await loop.run_in_executor(
            None, upload_file, settings.bucket_archives, archive_key, receipt_bytes, "application/json"
        )

        await db_svc.save_archive(
            contract_id,
            minio_key=archive_key,
            document_hash=document_hash,
            previous_seal_hash=previous_seal,
            seal_hash=seal_hash,
            receipt_data=receipt,
        )
        await db_svc.update_contract_status(contract_id, "archived")

        dur = int((time.monotonic() - t0) * 1000)
        await db_svc.complete_agent_step(
            step_id,
            output_data={"seal_hash": seal_hash[:16] + "…", "archive_key": archive_key},
            duration_ms=dur,
        )
        logger.info("contract_archived", contract_id=contract_id, seal=seal_hash[:16])
        return {}

    except Exception as exc:
        dur = int((time.monotonic() - t0) * 1000)
        await db_svc.complete_agent_step(step_id, status="failed", error_message=str(exc), duration_ms=dur)
        await db_svc.update_contract_status(contract_id, "failed")
        logger.error("archive_failed", contract_id=contract_id, error=str(exc))
        raise
