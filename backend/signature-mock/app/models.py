from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SigningEnvelope(Base):
    __tablename__ = "signing_envelopes"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    contract_id: Mapped[str] = mapped_column(String(255), nullable=False)
    document_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    callback_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    signers: Mapped[list["SigningEnvelopeSigner"]] = relationship(
        "SigningEnvelopeSigner",
        back_populates="envelope",
        order_by="SigningEnvelopeSigner.signing_order",
    )


class SigningEnvelopeSigner(Base):
    __tablename__ = "signing_envelope_signers"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    envelope_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("signing_envelopes.id", ondelete="CASCADE"), nullable=False)
    signer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    signer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    signing_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    signing_token: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signature_xml: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    envelope: Mapped["SigningEnvelope"] = relationship("SigningEnvelope", back_populates="signers")
