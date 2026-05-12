"""Node 3 — classify contract and propose signature workflow using Claude (smart model)."""
import json
import time

import structlog

from app.config import settings
from app.prompts import classification as prompt
from app.schemas.state import ContractState
from app.services import db as db_svc
from app.services.llm import call_tool

logger = structlog.get_logger()


async def classify(state: ContractState) -> dict:
    contract_id = state["contract_id"]
    step_id = await db_svc.create_agent_step(contract_id, "classify")
    t0 = time.monotonic()

    try:
        extracted_meta = {
            k: state.get(k)
            for k in ["parties", "amount", "currency", "start_date", "end_date",
                      "jurisdiction", "payment_terms"]
            if state.get(k) is not None
        }

        result, tok_in, tok_out = await call_tool(
            model=settings.llm_model_smart,
            system=prompt.SYSTEM,
            user=prompt.user_prompt(state["pdf_text"], extracted_meta),
            tool=prompt.TOOL,
            trace_name="classify",
        )

        db_data = {
            "contract_type": result["contract_type"],
            "risk_level": result["risk_level"],
            "classification_justification": result["classification_justification"],
            "sensitive_clauses": json.dumps(result.get("sensitive_clauses", [])),
            "proposed_workflow": json.dumps(result["proposed_workflow"]),
        }
        await db_svc.upsert_contract_metadata(contract_id, db_data)
        await db_svc.update_contract_status(contract_id, "awaiting_approval")

        dur = int((time.monotonic() - t0) * 1000)
        await db_svc.complete_agent_step(
            step_id,
            output_data={
                "contract_type": result["contract_type"],
                "risk_level": result["risk_level"],
                "sensitive_clauses_count": len(result.get("sensitive_clauses", [])),
            },
            tokens_input=tok_in,
            tokens_output=tok_out,
            duration_ms=dur,
        )
        logger.info("contract_classified", contract_id=contract_id,
                    type=result["contract_type"], risk=result["risk_level"])

        return {
            "contract_type": result["contract_type"],
            "risk_level": result["risk_level"],
            "classification_justification": result["classification_justification"],
            "sensitive_clauses": result.get("sensitive_clauses", []),
            "proposed_workflow": result["proposed_workflow"],
        }

    except Exception as exc:
        dur = int((time.monotonic() - t0) * 1000)
        await db_svc.complete_agent_step(step_id, status="failed", error_message=str(exc), duration_ms=dur)
        await db_svc.update_contract_status(contract_id, "failed")
        logger.error("classify_failed", contract_id=contract_id, error=str(exc))
        raise
