import uuid
from uuid import UUID

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models import Contract, ContractMetadata
from app.services.storage import delete_file, upload_file

logger = structlog.get_logger()


async def create_contract(
    db: AsyncSession,
    file_bytes: bytes,
    original_name: str,
) -> Contract:
    contract_id = uuid.uuid4()
    safe_name = original_name.replace(" ", "_")
    minio_key = upload_file(file_bytes, safe_name, contract_id)

    contract = Contract(
        id=contract_id,
        filename=safe_name,
        original_name=original_name,
        minio_key=minio_key,
        status="uploaded",
        file_size_bytes=len(file_bytes),
    )
    db.add(contract)
    await db.commit()
    await db.refresh(contract)
    return contract


async def trigger_agent(contract_id: UUID) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await client.post(
                f"{settings.agent_service_url}/process",
                json={"contract_id": str(contract_id)},
            )
        except Exception as exc:
            logger.warning("agent_trigger_failed", contract_id=str(contract_id), error=str(exc))


async def get_contract(db: AsyncSession, contract_id: UUID) -> Contract | None:
    result = await db.execute(
        select(Contract)
        .options(
            selectinload(Contract.contract_metadata),
            selectinload(Contract.steps),
            selectinload(Contract.signatures),
            selectinload(Contract.archive),
        )
        .where(Contract.id == contract_id)
    )
    return result.scalar_one_or_none()


async def list_contracts(db: AsyncSession) -> list[Contract]:
    result = await db.execute(select(Contract).order_by(Contract.created_at.desc()))
    return list(result.scalars().all())


async def delete_contract(db: AsyncSession, contract_id: UUID) -> bool:
    contract = await db.get(Contract, contract_id)
    if not contract:
        return False
    delete_file(contract.minio_bucket, contract.minio_key)
    await db.delete(contract)
    await db.commit()
    return True


async def approve_workflow(
    db: AsyncSession,
    contract_id: UUID,
    approved_signers: list[dict],
) -> Contract | None:
    result = await db.execute(
        select(ContractMetadata).where(ContractMetadata.contract_id == contract_id)
    )
    meta = result.scalar_one_or_none()
    if not meta:
        return None

    meta.approved_workflow = {"signers": approved_signers}
    await db.commit()

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await client.post(
                f"{settings.agent_service_url}/approve/{contract_id}",
                json={"approved_workflow": {"signers": approved_signers}},
            )
        except Exception as exc:
            logger.warning("agent_approve_failed", contract_id=str(contract_id), error=str(exc))

    return await get_contract(db, contract_id)
