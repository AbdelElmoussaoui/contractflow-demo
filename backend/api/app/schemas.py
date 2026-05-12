from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ContractMetadataOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    parties: list[dict] | None = None
    amount: Decimal | None = None
    currency: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    duration_months: int | None = None
    jurisdiction: str | None = None
    payment_terms: str | None = None
    contract_type: str | None = None
    risk_level: str | None = None
    classification_justification: str | None = None
    sensitive_clauses: list[dict] | None = None
    proposed_workflow: dict | None = None
    approved_workflow: dict | None = None


class AgentStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    step_name: str
    status: str
    output_data: dict | None = None
    error_message: str | None = None
    tokens_input: int | None = None
    tokens_output: int | None = None
    duration_ms: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class SignatureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    signer_name: str
    signer_email: str
    signing_order: int
    status: str
    signing_url: str | None = None
    signed_at: datetime | None = None
    verification_valid: bool | None = None


class ArchiveOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_hash: str
    seal_hash: str
    archive_timestamp: datetime
    receipt_data: dict


class ContractOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_name: str
    status: str
    file_size_bytes: int | None = None
    created_at: datetime
    updated_at: datetime


class ContractDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    original_name: str
    status: str
    file_size_bytes: int | None = None
    created_at: datetime
    updated_at: datetime
    # validation_alias reads from ORM attribute "contract_metadata"; JSON key is "metadata"
    metadata: ContractMetadataOut | None = Field(default=None, validation_alias="contract_metadata")
    steps: list[AgentStepOut] = []
    signatures: list[SignatureOut] = []
    archive: ArchiveOut | None = None


class WorkflowSigner(BaseModel):
    name: str
    email: str
    order: int = 1


class ApprovalIn(BaseModel):
    approved_workflow: list[WorkflowSigner]
