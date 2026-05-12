"""Node 6 — interrupt waiting for all signatures (resumed by signature webhook)."""
import structlog
from langgraph.types import interrupt

from app.schemas.state import ContractState
from app.services import db as db_svc

logger = structlog.get_logger()


async def wait_signatures(state: ContractState) -> dict:
    contract_id = state["contract_id"]
    step_id = await db_svc.create_agent_step(contract_id, "wait_signatures")
    await db_svc.set_step_waiting(step_id)

    # Pause graph — resumes when POST /webhooks/signature arrives with completed envelope
    resume_data: dict = interrupt({
        "message": "En attente des signatures",
        "envelope_id": state.get("envelope_id"),
    })

    signatures_data: list[dict] = resume_data.get("signatures", [])

    # Persist each received signature XML
    for sig in signatures_data:
        if sig.get("signature_xml"):
            await db_svc.update_signature_signed(
                contract_id,
                sig["email"],
                sig["signature_xml"],
            )

    await db_svc.complete_agent_step(
        step_id,
        output_data={"signatures_received": len(signatures_data)},
    )
    logger.info("signatures_received", contract_id=contract_id, count=len(signatures_data))
    return {"signatures_data": signatures_data}
