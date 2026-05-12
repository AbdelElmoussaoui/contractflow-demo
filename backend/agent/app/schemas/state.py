from typing import Any
from typing import TypedDict


class ContractState(TypedDict, total=False):
    # ── Required ──────────────────────────────────────────────────────────────
    contract_id: str
    minio_key: str
    minio_bucket: str

    # ── PDF content ───────────────────────────────────────────────────────────
    pdf_text: str

    # ── Extraction results ────────────────────────────────────────────────────
    parties: list[dict]
    amount: Any           # float | None
    currency: str
    start_date: str       # ISO date or None
    end_date: str
    duration_months: int
    jurisdiction: str
    payment_terms: str

    # ── Classification ────────────────────────────────────────────────────────
    contract_type: str    # commercial | rh | prestation | autre
    risk_level: str       # low | medium | high
    classification_justification: str
    sensitive_clauses: list[dict]
    proposed_workflow: dict  # {"signers": [...], "justification": "..."}

    # ── Approval ──────────────────────────────────────────────────────────────
    approved_workflow: dict  # {"signers": [...]}

    # ── Signature ─────────────────────────────────────────────────────────────
    envelope_id: str
    signatures_data: list[dict]

    # ── Error ─────────────────────────────────────────────────────────────────
    error: str
