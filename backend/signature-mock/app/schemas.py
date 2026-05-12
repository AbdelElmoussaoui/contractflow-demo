from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class SignerRequest(BaseModel):
    name: str
    email: str
    signing_order: int = 1


class EnvelopeCreateRequest(BaseModel):
    contract_id: str
    document_url: str
    filename: str
    callback_url: str | None = None
    signers: list[SignerRequest]


class SignerOut(BaseModel):
    id: UUID
    signer_name: str
    signer_email: str
    signing_order: int
    status: str
    signing_url: str | None = None
    signed_at: datetime | None = None

    model_config = {"from_attributes": True}


class EnvelopeOut(BaseModel):
    envelope_id: UUID
    contract_id: str
    status: str
    document_hash: str
    signers: list[SignerOut]
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}
