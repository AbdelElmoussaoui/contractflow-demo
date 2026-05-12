import asyncio
import json
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal, get_db
from app.schemas import ApprovalIn, ContractDetailOut, ContractOut
from app.services.contracts import (
    approve_workflow,
    create_contract,
    delete_contract,
    get_contract,
    list_contracts,
    trigger_agent,
)

router = APIRouter(prefix="/contracts", tags=["contracts"])
logger = structlog.get_logger()

_TERMINAL_STATUSES = {"archived", "failed"}
_ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}


@router.post("", response_model=ContractOut, status_code=status.HTTP_201_CREATED)
async def upload_contract(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in _ALLOWED_CONTENT_TYPES and not (
        file.filename or ""
    ).lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF files are accepted")

    file_bytes = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {settings.max_upload_mb} MB",
        )

    contract = await create_contract(db, file_bytes, file.filename or "contract.pdf")
    logger.info("contract_uploaded", contract_id=str(contract.id), filename=contract.original_name)

    asyncio.create_task(trigger_agent(contract.id))

    return contract


@router.get("", response_model=list[ContractOut])
async def get_contracts(db: AsyncSession = Depends(get_db)):
    return await list_contracts(db)


@router.get("/{contract_id}", response_model=ContractDetailOut)
async def get_contract_detail(
    contract_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    contract = await get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_contract(
    contract_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_contract(db, contract_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Contract not found")


@router.post("/{contract_id}/approve", response_model=ContractDetailOut)
async def approve_contract_workflow(
    contract_id: UUID,
    body: ApprovalIn,
    db: AsyncSession = Depends(get_db),
):
    signers = [s.model_dump() for s in body.approved_workflow]
    contract = await approve_workflow(db, contract_id, signers)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


@router.get("/{contract_id}/events")
async def contract_events(contract_id: UUID):
    async def event_generator():
        while True:
            async with AsyncSessionLocal() as db:
                contract = await get_contract(db, contract_id)

            if contract is None:
                yield f"event: error\ndata: {json.dumps({'detail': 'not found'})}\n\n"
                return

            payload = ContractDetailOut.model_validate(contract).model_dump(mode="json")
            yield f"data: {json.dumps(payload)}\n\n"

            if contract.status in _TERMINAL_STATUSES:
                return

            await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
