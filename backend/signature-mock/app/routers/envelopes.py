"""Envelopes router — DocuSign-like mock endpoints."""
from __future__ import annotations

import asyncio
import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from uuid import UUID

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import AsyncSessionLocal, get_db
from app.models import SigningEnvelope, SigningEnvelopeSigner
from app.schemas import EnvelopeCreateRequest, EnvelopeOut, SignerOut
from app.services.notifier import notify_agent
from app.services.signing import generate_signature_xml

router = APIRouter()
logger = structlog.get_logger()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _load_envelope(db: AsyncSession, envelope_id: UUID) -> SigningEnvelope | None:
    result = await db.execute(
        select(SigningEnvelope)
        .options(selectinload(SigningEnvelope.signers))
        .where(SigningEnvelope.id == envelope_id)
    )
    return result.scalar_one_or_none()


def _signing_url(token: str) -> str:
    return f"{settings.public_base_url}/sign/{token}"


def _signer_to_dict(s: SigningEnvelopeSigner) -> dict:
    return {
        "name": s.signer_name,
        "email": s.signer_email,
        "signed_at": s.signed_at.isoformat() if s.signed_at else None,
        "signature_xml": s.signature_xml or "",
    }


# ── Auto-sign background task ─────────────────────────────────────────────────

async def _auto_sign_envelope(envelope_id: str) -> None:
    """Simulate sequential human signing with realistic delays."""
    await asyncio.sleep(settings.auto_sign_initial_delay)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SigningEnvelope)
            .options(selectinload(SigningEnvelope.signers))
            .where(SigningEnvelope.id == envelope_id)
        )
        envelope = result.scalar_one_or_none()
        if not envelope:
            return

    # Group signers by signing_order and process sequentially
    orders: dict[int, list] = {}
    for s in sorted(envelope.signers, key=lambda x: x.signing_order):
        orders.setdefault(s.signing_order, []).append(s)

    for order in sorted(orders):
        for signer in orders[order]:
            await asyncio.sleep(settings.auto_sign_interval)
            await _do_sign(str(signer.signing_token), auto=True)

    # Check completion after all orders
    await _maybe_complete_envelope(envelope_id)


async def _do_sign(token: str, auto: bool = False) -> SigningEnvelopeSigner | None:
    """Generate signature XML and mark signer as signed."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SigningEnvelopeSigner)
            .options(selectinload(SigningEnvelopeSigner.envelope))
            .where(SigningEnvelopeSigner.signing_token == token)
        )
        signer = result.scalar_one_or_none()
        if not signer or signer.status == "signed":
            return signer

        envelope = signer.envelope
        now = datetime.now(timezone.utc)
        sig_xml = generate_signature_xml(
            document_hash_hex=envelope.document_hash,
            signer_name=signer.signer_name,
            signer_email=signer.signer_email,
            signed_at=now,
        )
        signer.status = "signed"
        signer.signed_at = now
        signer.signature_xml = sig_xml
        await db.commit()

        logger.info(
            "signer_signed",
            envelope_id=str(envelope.id),
            signer=signer.signer_email,
            auto=auto,
        )
        return signer


async def _maybe_complete_envelope(envelope_id: str) -> None:
    """If all signers have signed, mark envelope completed and fire webhook."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SigningEnvelope)
            .options(selectinload(SigningEnvelope.signers))
            .where(SigningEnvelope.id == envelope_id)
        )
        envelope = result.scalar_one_or_none()
        if not envelope or envelope.status == "completed":
            return

        pending = [s for s in envelope.signers if s.status != "signed"]
        if pending:
            # Update to partially_signed
            envelope.status = "partially_signed"
            await db.commit()
            return

        envelope.status = "completed"
        envelope.completed_at = datetime.now(timezone.utc)
        await db.commit()

        signers_payload = [_signer_to_dict(s) for s in envelope.signers]
        callback_url = envelope.callback_url
        contract_id = envelope.contract_id
        eid = str(envelope.id)

    logger.info("envelope_completed", envelope_id=eid, contract_id=contract_id)
    await notify_agent(
        envelope_id=eid,
        contract_id=contract_id,
        callback_url=callback_url,
        signers=signers_payload,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/envelopes", response_model=EnvelopeOut, status_code=201)
async def create_envelope(body: EnvelopeCreateRequest, db: AsyncSession = Depends(get_db)):
    # Download document to compute SHA-256 hash
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(body.document_url)
            resp.raise_for_status()
            doc_bytes = resp.content
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Cannot download document: {exc}")

    doc_hash = hashlib.sha256(doc_bytes).hexdigest()

    envelope = SigningEnvelope(
        contract_id=body.contract_id,
        document_hash=doc_hash,
        filename=body.filename,
        status="pending",
        callback_url=body.callback_url or settings.agent_callback_url,
    )
    db.add(envelope)
    await db.flush()  # get envelope.id before adding signers

    for req_signer in body.signers:
        token = secrets.token_urlsafe(32)
        signer = SigningEnvelopeSigner(
            envelope_id=envelope.id,
            signer_name=req_signer.name,
            signer_email=req_signer.email,
            signing_order=req_signer.signing_order,
            status="pending",
            signing_token=token,
        )
        db.add(signer)

    await db.commit()
    await db.refresh(envelope)

    # Reload with signers for response
    envelope = await _load_envelope(db, envelope.id)

    logger.info(
        "envelope_created",
        envelope_id=str(envelope.id),
        contract_id=body.contract_id,
        signers=len(envelope.signers),
    )

    # Start auto-sign in the background
    asyncio.create_task(_auto_sign_envelope(str(envelope.id)))

    # Build response with signing URLs
    signers_out = [
        SignerOut(
            id=s.id,
            signer_name=s.signer_name,
            signer_email=s.signer_email,
            signing_order=s.signing_order,
            status=s.status,
            signing_url=_signing_url(s.signing_token),
            signed_at=s.signed_at,
        )
        for s in envelope.signers
    ]

    return EnvelopeOut(
        envelope_id=envelope.id,
        contract_id=envelope.contract_id,
        status=envelope.status,
        document_hash=envelope.document_hash,
        signers=signers_out,
        created_at=envelope.created_at,
        completed_at=envelope.completed_at,
    )


@router.get("/envelopes/{envelope_id}", response_model=EnvelopeOut)
async def get_envelope(envelope_id: UUID, db: AsyncSession = Depends(get_db)):
    envelope = await _load_envelope(db, envelope_id)
    if not envelope:
        raise HTTPException(status_code=404, detail="Envelope not found")

    signers_out = [
        SignerOut(
            id=s.id,
            signer_name=s.signer_name,
            signer_email=s.signer_email,
            signing_order=s.signing_order,
            status=s.status,
            signing_url=_signing_url(s.signing_token) if s.signing_token else None,
            signed_at=s.signed_at,
        )
        for s in envelope.signers
    ]
    return EnvelopeOut(
        envelope_id=envelope.id,
        contract_id=envelope.contract_id,
        status=envelope.status,
        document_hash=envelope.document_hash,
        signers=signers_out,
        created_at=envelope.created_at,
        completed_at=envelope.completed_at,
    )


@router.get("/sign/{token}", response_class=HTMLResponse)
async def sign_document(token: str):
    """Signing page — opening this URL triggers the signature (demo behaviour)."""
    signer = await _do_sign(token)

    if signer is None:
        return HTMLResponse(
            content=_sign_page("Lien invalide", "Ce lien de signature est invalide ou a déjà expiré.", error=True),
            status_code=404,
        )

    envelope_id = str(signer.envelope_id)
    asyncio.create_task(_maybe_complete_envelope(envelope_id))

    return HTMLResponse(
        content=_sign_page(
            f"Document signé — {signer.signer_name}",
            f"Votre signature a été apposée avec succès sur le document.<br>"
            f"<strong>Signataire :</strong> {signer.signer_name} ({signer.signer_email})<br>"
            f"<strong>Date :</strong> {signer.signed_at.strftime('%d/%m/%Y à %H:%M:%S UTC') if signer.signed_at else ''}",
        ),
    )


def _sign_page(title: str, message: str, error: bool = False) -> str:
    color = "#dc2626" if error else "#16a34a"
    icon = "✗" if error else "✓"
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: system-ui, sans-serif; background: #f8fafc; display: flex;
            align-items: center; justify-content: center; min-height: 100vh; }}
    .card {{ background: white; border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,.08);
             padding: 48px 40px; max-width: 480px; width: 90%; text-align: center; }}
    .icon {{ font-size: 56px; color: {color}; margin-bottom: 20px; }}
    h1 {{ font-size: 22px; color: #1e293b; margin-bottom: 16px; }}
    p {{ color: #64748b; line-height: 1.6; font-size: 15px; }}
    .badge {{ display: inline-block; margin-top: 24px; padding: 6px 16px;
              background: {color}20; color: {color}; border-radius: 999px;
              font-size: 13px; font-weight: 600; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">{icon}</div>
    <h1>{title}</h1>
    <p>{message}</p>
    <div class="badge">ContractFlow Demo Mock</div>
  </div>
</body>
</html>"""
