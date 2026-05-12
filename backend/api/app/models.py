from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger, Boolean, Date, DateTime, ForeignKey,
    Integer, Numeric, String, Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    minio_bucket: Mapped[str] = mapped_column(String(100), nullable=False, default="contracts")
    minio_key: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="uploaded")
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    contract_metadata: Mapped["ContractMetadata | None"] = relationship(
        "ContractMetadata", back_populates="contract", uselist=False, lazy="select"
    )
    steps: Mapped[list["AgentStep"]] = relationship(
        "AgentStep", back_populates="contract", order_by="AgentStep.created_at"
    )
    signatures: Mapped[list["Signature"]] = relationship(
        "Signature", back_populates="contract", order_by="Signature.signing_order"
    )
    archive: Mapped["Archive | None"] = relationship(
        "Archive", back_populates="contract", uselist=False
    )


class ContractMetadata(Base):
    __tablename__ = "contract_metadata"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    contract_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    parties: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), default="EUR")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    duration_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    contract_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    classification_justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    sensitive_clauses: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    proposed_workflow: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    approved_workflow: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    contract: Mapped["Contract"] = relationship("Contract", back_populates="contract_metadata")


class AgentStep(Base):
    __tablename__ = "agent_steps"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    contract_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    step_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    input_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    tokens_input: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_output: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    contract: Mapped["Contract"] = relationship("Contract", back_populates="steps")


class Signature(Base):
    __tablename__ = "signatures"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    contract_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    envelope_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    signer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    signer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    signing_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    signing_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signature_xml: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    verification_hash_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    verification_cert_subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    verification_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    contract: Mapped["Contract"] = relationship("Contract", back_populates="signatures")


class Archive(Base):
    __tablename__ = "archives"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    contract_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    minio_bucket: Mapped[str] = mapped_column(String(100), nullable=False, default="archives")
    minio_key: Mapped[str] = mapped_column(String(500), nullable=False)
    document_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_seal_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    seal_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    archive_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    receipt_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    contract: Mapped["Contract"] = relationship("Contract", back_populates="archive")
