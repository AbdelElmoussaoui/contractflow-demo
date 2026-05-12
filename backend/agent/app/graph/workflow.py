"""LangGraph StateGraph — ContractFlow processing pipeline.

Flow:
  load_pdf → extract_metadata → classify
    → [INTERRUPT] human_review
    → create_envelope
    → [INTERRUPT] wait_signatures
    → verify_signatures → archive → END
"""
from __future__ import annotations

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from psycopg_pool import AsyncConnectionPool

from app.config import settings
from app.nodes.archive import archive
from app.nodes.classify import classify
from app.nodes.create_envelope import create_envelope
from app.nodes.extract_metadata import extract_metadata
from app.nodes.human_review import human_review
from app.nodes.load_pdf import load_pdf
from app.nodes.verify_signatures import verify_signatures
from app.nodes.wait_signatures import wait_signatures
from app.schemas.state import ContractState

# Lazily initialised in build_graph()
_graph = None
_pool: AsyncConnectionPool | None = None


def _build_workflow() -> StateGraph:
    wf = StateGraph(ContractState)

    wf.add_node("load_pdf", load_pdf)
    wf.add_node("extract_metadata", extract_metadata)
    wf.add_node("classify", classify)
    wf.add_node("human_review", human_review)
    wf.add_node("create_envelope", create_envelope)
    wf.add_node("wait_signatures", wait_signatures)
    wf.add_node("verify_signatures", verify_signatures)
    wf.add_node("archive", archive)

    wf.add_edge(START, "load_pdf")
    wf.add_edge("load_pdf", "extract_metadata")
    wf.add_edge("extract_metadata", "classify")
    wf.add_edge("classify", "human_review")
    wf.add_edge("human_review", "create_envelope")
    wf.add_edge("create_envelope", "wait_signatures")
    wf.add_edge("wait_signatures", "verify_signatures")
    wf.add_edge("verify_signatures", "archive")
    wf.add_edge("archive", END)

    return wf


async def get_graph():
    """Return (and lazily initialise) the compiled graph with its checkpointer."""
    global _graph, _pool

    if _graph is not None:
        return _graph

    _pool = AsyncConnectionPool(
        conninfo=settings.database_url_sync,
        max_size=10,
        open=False,
    )
    await _pool.open()

    checkpointer = AsyncPostgresSaver(_pool)
    await checkpointer.setup()

    _graph = _build_workflow().compile(checkpointer=checkpointer, interrupt_before=[])
    return _graph


async def close_graph() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
