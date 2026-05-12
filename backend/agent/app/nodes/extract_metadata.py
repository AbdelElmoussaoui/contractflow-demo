"""Node 2 — extract structured metadata from PDF text using Claude (fast model)."""
import time

import structlog

from app.config import settings
from app.prompts import extraction as prompt
from app.schemas.state import ContractState
from app.services import db as db_svc
from app.services.llm import call_tool

logger = structlog.get_logger()


async def extract_metadata(state: ContractState) -> dict:
    contract_id = state["contract_id"]
    step_id = await db_svc.create_agent_step(contract_id, "extract_metadata")
    t0 = time.monotonic()

    try:
        result, tok_in, tok_out = await call_tool(
            model=settings.llm_model_fast,
            system=prompt.SYSTEM,
            user=prompt.user_prompt(state["pdf_text"]),
            tool=prompt.TOOL,
            trace_name="extract_metadata",
        )

        metadata_update = {
            k: result.get(k)
            for k in [
                "parties", "amount", "currency", "start_date", "end_date",
                "duration_months", "jurisdiction", "payment_terms",
            ]
            if result.get(k) is not None
        }

        # Serialize dates and JSONB fields for raw SQL
        import json
        db_data: dict = {}
        for k, v in metadata_update.items():
            if isinstance(v, list):
                db_data[k] = json.dumps(v)
            else:
                db_data[k] = v

        await db_svc.upsert_contract_metadata(contract_id, db_data)

        dur = int((time.monotonic() - t0) * 1000)
        await db_svc.complete_agent_step(
            step_id,
            output_data={"parties_count": len(result.get("parties", []))},
            tokens_input=tok_in,
            tokens_output=tok_out,
            duration_ms=dur,
        )
        logger.info("metadata_extracted", contract_id=contract_id, parties=len(result.get("parties", [])))
        return metadata_update

    except Exception as exc:
        dur = int((time.monotonic() - t0) * 1000)
        await db_svc.complete_agent_step(step_id, status="failed", error_message=str(exc), duration_ms=dur)
        await db_svc.update_contract_status(contract_id, "failed")
        logger.error("extract_metadata_failed", contract_id=contract_id, error=str(exc))
        raise
