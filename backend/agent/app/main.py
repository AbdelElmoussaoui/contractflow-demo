import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.types import Command
from pydantic import BaseModel

from app.config import settings
from app.graph.workflow import close_graph, get_graph

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(logging, settings.log_level.upper(), logging.INFO)
    ),
)

logger = structlog.get_logger()


# ── Lifespan (replaces deprecated @app.on_event) ─────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_graph()
    logger.info("agent_ready")
    yield
    await close_graph()


app = FastAPI(title="ContractFlow Agent", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _thread(contract_id: str) -> dict:
    return {"configurable": {"thread_id": contract_id}}


async def _run_graph(contract_id: str) -> None:
    graph = await get_graph()
    try:
        await graph.ainvoke({"contract_id": contract_id}, config=_thread(contract_id))
    except Exception as exc:
        logger.error("graph_run_error", contract_id=contract_id, error=str(exc))


async def _resume_graph(contract_id: str, resume_value: dict) -> None:
    graph = await get_graph()
    try:
        await graph.ainvoke(Command(resume=resume_value), config=_thread(contract_id))
    except Exception as exc:
        logger.error("graph_resume_error", contract_id=contract_id, error=str(exc))


# ── Endpoints ─────────────────────────────────────────────────────────────────

class ProcessRequest(BaseModel):
    contract_id: str


class ApprovalRequest(BaseModel):
    approved_workflow: dict


class SignatureWebhook(BaseModel):
    envelope_id: str
    contract_id: str
    status: str
    signers: list[dict]


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/process")
async def process_contract(body: ProcessRequest, background_tasks: BackgroundTasks):
    logger.info("process_request", contract_id=body.contract_id)
    background_tasks.add_task(_run_graph, body.contract_id)
    return {"status": "processing", "contract_id": body.contract_id}


@app.post("/approve/{contract_id}")
async def approve_workflow(
    contract_id: str,
    body: ApprovalRequest,
    background_tasks: BackgroundTasks,
):
    logger.info("approve_request", contract_id=contract_id)
    background_tasks.add_task(_resume_graph, contract_id, {"approved_workflow": body.approved_workflow})
    return {"status": "resuming", "contract_id": contract_id}


@app.post("/webhooks/signature")
async def signature_webhook(body: SignatureWebhook, background_tasks: BackgroundTasks):
    logger.info(
        "signature_webhook",
        contract_id=body.contract_id,
        status=body.status,
        envelope_id=body.envelope_id,
    )

    if body.status != "completed":
        return {"status": "ignored", "reason": "envelope not yet completed"}

    resume_value = {
        "signatures": [
            {
                "name": s.get("name", ""),
                "email": s.get("email", ""),
                "signed_at": s.get("signed_at"),
                "signature_xml": s.get("signature_xml", ""),
            }
            for s in body.signers
        ]
    }
    background_tasks.add_task(_resume_graph, body.contract_id, resume_value)
    return {"status": "resuming", "contract_id": body.contract_id}
