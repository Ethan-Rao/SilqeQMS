from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.eqms.models import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    doc_number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(64), nullable=False)

    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    # Draft -> Released -> Obsolete
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="Draft")

    current_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_revisions.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)

    revisions: Mapped[list["DocumentRevision"]] = relationship(
        "DocumentRevision",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="DocumentRevision.document_id",
    )

    current_revision: Mapped["DocumentRevision | None"] = relationship(
        "DocumentRevision",
        foreign_keys=[current_revision_id],
        lazy="selectin",
        post_update=True,
    )


class DocumentRevision(Base):
    __tablename__ = "document_revisions"
    __table_args__ = (
        UniqueConstraint("document_id", "revision", name="uq_document_revision"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    revision: Mapped[str] = mapped_column(String(16), nullable=False)  # e.g. "A", "B", "1"

    change_summary: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    released_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    document: Mapped[Document] = relationship(
        "Document",
        back_populates="revisions",
        foreign_keys=[document_id],
        lazy="selectin",
    )

    files: Mapped[list["DocumentFile"]] = relationship(
        "DocumentFile",
        back_populates="revision",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class DocumentFile(Base):
    __tablename__ = "document_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    revision_id: Mapped[int] = mapped_column(ForeignKey("document_revisions.id", ondelete="CASCADE"), nullable=False)

    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False, default="application/octet-stream")
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    revision: Mapped[DocumentRevision] = relationship(
        "DocumentRevision",
        back_populates="files",
        lazy="selectin",
    )

