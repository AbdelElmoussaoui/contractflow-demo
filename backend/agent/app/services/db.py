"""Helpers to update the shared PostgreSQL database from agent nodes."""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal


# ── ORM-free helpers (raw SQL for simplicity in background tasks) ─────────────

async def update_contract_status(contract_id: str, status: str) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("UPDATE contracts SET status = :status, updated_at = NOW() WHERE id = :id"),
            {"status": status, "id": contract_id},
        )
        await db.commit()


async def upsert_contract_metadata(contract_id: str, data: dict) -> None:
    async with AsyncSessionLocal() as db:
        existing = await db.execute(
            text("SELECT id FROM contract_metadata WHERE contract_id = :cid"),
            {"cid": contract_id},
        )
        row = existing.fetchone()
        if row:
            set_clauses = ", ".join(f"{k} = :{k}" for k in data)
            await db.execute(
                text(f"UPDATE contract_metadata SET {set_clauses} WHERE contract_id = :contract_id"),
                {**data, "contract_id": contract_id},
            )
        else:
            cols = "contract_id, " + ", ".join(data.keys())
            vals = ":contract_id, " + ", ".join(f":{k}" for k in data)
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
                "UPDATE agent_steps SET status=:status, output_data=:out::jsonb, "
                "error_message=:err, tokens_input=:ti, tokens_output=:to_, "
                "duration_ms=:dur, completed_at=NOW() WHERE id=:id"
            ),
            {
                "status": status,
                "out": __import__("json").dumps(output_data) if output_data else None,
                "err": error_message,
                "ti": tokens_input,
                "to_": tokens_output,
                "dur": duration_ms,
                "id": step_id,
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
        # Remove previous pending signatures (idempotent re-send case)
        await db.execute(
            text("DELETE FROM signatures WHERE contract_id = :cid AND status = 'pending'"),
            {"cid": contract_id},
        )
        for s in signers:
            await db.execute(
                text(
                    "INSERT INTO signatures (contract_id, envelope_id, signer_name, signer_email, "
                    "signing_order, status, signing_url) "
                    "VALUES (:cid, :env, :name, :email, :ord, 'sent', :url)"
                ),
                {
                    "cid": contract_id,
                    "env": envelope_id,
                    "name": s.get("name"),
                    "email": s.get("email"),
                    "ord": s.get("order", 1),
                    "url": s.get("signing_url"),
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
                "UPDATE signatures SET status=:status, verification_valid=:valid, "
                "verification_hash_match=:hm, verification_cert_subject=:cert, "
                "verification_error=:err, verified_at=NOW() "
                "WHERE contract_id=:cid AND signer_email=:email"
            ),
            {
                "status": "verified" if valid else "failed",
                "valid": valid,
                "hm": hash_match,
                "cert": cert_subject,
                "err": error,
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
                "INSERT INTO archives (contract_id, minio_key, document_hash, previous_seal_hash, "
                "seal_hash, receipt_data) "
                "VALUES (:cid, :key, :dh, :psh, :sh, :rd::jsonb) "
                "ON CONFLICT (contract_id) DO UPDATE SET "
                "minio_key=EXCLUDED.minio_key, document_hash=EXCLUDED.document_hash, "
                "seal_hash=EXCLUDED.seal_hash, receipt_data=EXCLUDED.receipt_data"
            ),
            {
                "cid": contract_id,
                "key": minio_key,
                "dh": document_hash,
                "psh": previous_seal_hash,
                "sh": seal_hash,
                "rd": __import__("json").dumps(receipt_data),
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
