"""Node 5 — create signing envelope in the signature-mock service."""
import time

import httpx
import structlog

from app.config import settings
from app.schemas.state import ContractState
from app.services import db as db_svc
from app.services.storage import get_presigned_url

logger = structlog.get_logger()


async def create_envelope(state: ContractState) -> dict:
    contract_id = state["contract_id"]
    step_id = await db_svc.create_agent_step(contract_id, "create_envelope")
    t0 = time.monotonic()

    try:
        approved = state.get("approved_workflow", {})
        signers = approved.get("signers", [])

        # Build presigned download URL for the PDF
        doc_url = get_presigned_url(
            state.get("minio_bucket", settings.bucket_contracts),
            state["minio_key"],
        )

        payload = {
            "contract_id": contract_id,
            "document_url": doc_url,
            "filename": state["minio_key"].split("/")[-1],
            # callback_url omitted — mock uses its configured AGENT_CALLBACK_URL
            "signers": [
                {"name": s["name"], "email": s["email"], "signing_order": s.get("order", 1)}
                for s in signers
            ],
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{settings.signature_mock_url}/envelopes", json=payload)
            resp.raise_for_status()
            envelope = resp.json()

        envelope_id = envelope["envelope_id"]
        mock_signers = envelope.get("signers", [])

        # Merge signing_url back into signers list
        url_map = {s["email"]: s.get("signing_url") for s in mock_signers}
        for s in signers:
            s["signing_url"] = url_map.get(s["email"])

        await db_svc.upsert_signatures(contract_id, signers, envelope_id)
        await db_svc.update_contract_status(contract_id, "awaiting_signatures")

        dur = int((time.monotonic() - t0) * 1000)
        await db_svc.complete_agent_step(
            step_id,
            output_data={"envelope_id": envelope_id, "signers_count": len(signers)},
            duration_ms=dur,
        )
        logger.info("envelope_created", contract_id=contract_id, envelope_id=envelope_id)
        return {"envelope_id": envelope_id}

    except Exception as exc:
        dur = int((time.monotonic() - t0) * 1000)
        await db_svc.complete_agent_step(step_id, status="failed", error_message=str(exc), duration_ms=dur)
        await db_svc.update_contract_status(contract_id, "failed")
        logger.error("create_envelope_failed", contract_id=contract_id, error=str(exc))
        raise
