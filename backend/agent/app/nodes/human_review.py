"""Node 4 — interrupt for human approval of the proposed workflow."""
import json

import structlog
from langgraph.types import interrupt

from app.schemas.state import ContractState
from app.services import db as db_svc

logger = structlog.get_logger()


async def human_review(state: ContractState) -> dict:
    contract_id = state["contract_id"]
    step_id = await db_svc.create_agent_step(contract_id, "human_review")
    await db_svc.set_step_waiting(step_id)

    # Pause graph — resumes when /approve/{contract_id} is called
    resume_data: dict = interrupt({
        "message": "En attente de validation humaine",
        "proposed_workflow": state.get("proposed_workflow"),
    })

    # Execution resumes here with resume_data from Command(resume=...)
    approved_workflow: dict = resume_data.get("approved_workflow", {})

    await db_svc.upsert_contract_metadata(
        contract_id,
        {"approved_workflow": json.dumps(approved_workflow)},
    )
    await db_svc.complete_agent_step(
        step_id,
        output_data={"signers_count": len(approved_workflow.get("signers", []))},
    )
    logger.info("workflow_approved", contract_id=contract_id,
                signers=len(approved_workflow.get("signers", [])))
    return {"approved_workflow": approved_workflow}
