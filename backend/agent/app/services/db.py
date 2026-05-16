"""Helpers to update the shared PostgreSQL database from agent nodes.

IMPORTANT — cast JSONB : asyncpg ne supporte pas la syntaxe :param::jsonb
(le :: confond le parser de paramètres nommés). On utilise CAST(:param AS jsonb).
"""
from __future__ import annotations

import json

from sqlalchemy import text

from app.database import AsyncSessionLocal

# Colonnes JSONB dans contract_metadata
_JSONB_COLS = frozenset({"parties", "sensitive_clauses", "proposed_workflow", "approved_workflow"})

# Whitelist pour éviter l'injection SQL via les noms de colonnes
_ALLOWED_META_COLS = frozenset({
    "parties", "amount", "currency", "start_date", "end_date",
    "duration_months", "jurisdiction", "payment_terms",
    "contract_type", "risk_level", "classification_justification",
    "sensitive_clauses", "proposed_workflow", "approved_workflow",
})


async def update_contract_status(contract_id: str, status: str) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("UPDATE contracts SET status = :status, updated_at = NOW() WHERE id = :id"),
            {"status": status, "id": contract_id},
        )
        await db.commit()


async def upsert_contract_metadata(contract_id: str, data: dict) -> None:
    unknown = set(data) - _ALLOWED_META_COLS
    if unknown:
        raise ValueError(f"Colonnes contract_metadata inconnues : {unknown}")

    async with AsyncSessionLocal() as db:
        existing = await db.execute(
            text("SELECT id FROM contract_metadata WHERE contract_id = :cid"),
            {"cid": contract_id},
        )
        row = existing.fetchone()

        # CAST(:k AS jsonb) au lieu de :k::jsonb — asyncpg ne supporte pas ::
        def _assign(k: str) -> str:
            return f"{k} = CAST(:{k} AS jsonb)" if k in _JSONB_COLS else f"{k} = :{k}"

        def _value(k: str) -> str:
            return f"CAST(:{k} AS jsonb)" if k in _JSONB_COLS else f":{k}"

        if row:
            set_clauses = ", ".join(_assign(k) for k in data)
            await db.execute(
                text(f"UPDATE contract_metadata SET {set_clauses} WHERE contract_id = :contract_id"),
                {**data, "contract_id": contract_id},
            )
        else:
            cols = "contract_id, " + ", ".join(data.keys())
            vals = ":contract_id, " + ", ".join(_value(k) for k in data)
            await db.execute(
                text(f"INSERT INTO contract_metadata ({cols}) VALUES ({vals})"),
                {**data, "contract_id": contract_id},
            )
        await db.commit()


async def create_agent_step(contract_id: str, step_name: str) -> str:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text(
                "INSERT INTO agent_steps (contract_id, step_name, status, started_at) "
                "VALUES (:cid, :name, 'running', NOW()) RETURNING id"
            ),
            {"cid": contract_id, "name": step_name},
        )
        step_id = str(result.fetchone()[0])
        await db.commit()
    return step_id


async def complete_agent_step(
    step_id: str,
    *,
    status: str = "done",
    output_data: dict | None = None,
    error_message: str | None = None,
    tokens_input: int | None = None,
    tokens_output: int | None = None,
    duration_ms: int | None = None,
) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            text(
                "UPDATE agent_steps "
                "SET status=:status, "
                "    output_data=CAST(:out_data AS jsonb), "
                "    error_message=:err_msg, "
                "    tokens_input=:tok_in, "
                "    tokens_output=:tok_out, "
                "    duration_ms=:dur_ms, "
                "    completed_at=NOW() "
                "WHERE id=:step_id"
            ),
            {
                "status": status,
                "out_data": json.dumps(output_data) if output_data else None,
                "err_msg": error_message,
                "tok_in": tokens_input,
                "tok_out": tokens_output,
                "dur_ms": duration_ms,
                "step_id": step_id,
            },
        )
        await db.commit()


async def set_step_waiting(step_id: str) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("UPDATE agent_steps SET status = 'waiting' WHERE id = :id"),
            {"id": step_id},
        )
        await db.commit()


async def upsert_signatures(contract_id: str, signers: list[dict], envelope_id: str) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("DELETE FROM signatures WHERE contract_id = :cid AND status = 'pending'"),
            {"cid": contract_id},
        )
        for s in signers:
            await db.execute(
                text(
                    "INSERT INTO signatures "
                    "(contract_id, envelope_id, signer_name, signer_email, signing_order, status, signing_url) "
                    "VALUES (:cid, :env, :sname, :semail, :sord, 'sent', :surl)"
                ),
                {
                    "cid": contract_id,
                    "env": envelope_id,
                    "sname": s.get("name"),
                    "semail": s.get("email"),
                    "sord": s.get("order", 1),
                    "surl": s.get("signing_url"),
                },
            )
        await db.commit()


async def update_signature_signed(contract_id: str, signer_email: str, sig_xml: str) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            text(
                "UPDATE signatures SET status='signed', signature_xml=:xml, signed_at=NOW() "
                "WHERE contract_id=:cid AND signer_email=:email"
            ),
            {"xml": sig_xml, "cid": contract_id, "email": signer_email},
        )
        await db.commit()


async def update_signature_verified(
    contract_id: str,
    signer_email: str,
    *,
    valid: bool,
    hash_match: bool,
    cert_subject: str | None = None,
    error: str | None = None,
) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            text(
                "UPDATE signatures "
                "SET status=:vstatus, verification_valid=:vvalid, "
                "    verification_hash_match=:vhm, verification_cert_subject=:vcert, "
                "    verification_error=:verr, verified_at=NOW() "
                "WHERE contract_id=:cid AND signer_email=:email"
            ),
            {
                "vstatus": "verified" if valid else "failed",
                "vvalid": valid,
                "vhm": hash_match,
                "vcert": cert_subject,
                "verr": error,
                "cid": contract_id,
                "email": signer_email,
            },
        )
        await db.commit()


async def save_archive(
    contract_id: str,
    *,
    minio_key: str,
    document_hash: str,
    previous_seal_hash: str | None,
    seal_hash: str,
    receipt_data: dict,
) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            text(
                "INSERT INTO archives "
                "(contract_id, minio_key, document_hash, previous_seal_hash, seal_hash, receipt_data) "
                "VALUES (:cid, :mkey, :dhash, :prev_seal, :shash, CAST(:rdata AS jsonb)) "
                "ON CONFLICT (contract_id) DO UPDATE SET "
                "minio_key=EXCLUDED.minio_key, document_hash=EXCLUDED.document_hash, "
                "seal_hash=EXCLUDED.seal_hash, receipt_data=EXCLUDED.receipt_data"
            ),
            {
                "cid": contract_id,
                "mkey": minio_key,
                "dhash": document_hash,
                "prev_seal": previous_seal_hash,
                "shash": seal_hash,
                "rdata": json.dumps(receipt_data),
            },
        )
        await db.commit()


async def get_latest_seal_hash() -> str | None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text("SELECT seal_hash FROM archives ORDER BY archive_timestamp DESC LIMIT 1")
        )
        row = result.fetchone()
        return row[0] if row else None


async def get_contract_minio_info(contract_id: str) -> tuple[str, str] | None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text("SELECT minio_bucket, minio_key FROM contracts WHERE id = :id"),
            {"id": contract_id},
        )
        row = result.fetchone()
        return (row[0], row[1]) if row else None
