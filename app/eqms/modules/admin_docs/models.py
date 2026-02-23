from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.eqms.models import Base


class AdminDocFolder(Base):
    __tablename__ = "admin_doc_folders"
    __table_args__ = (
        Index("idx_admin_doc_folders_library", "library_key"),
        Index("idx_admin_doc_folders_parent", "parent_id"),
        UniqueConstraint("library_key", "parent_id", "name", name="uq_admin_doc_folder_path"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    library_key: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("admin_doc_folders.id", ondelete="CASCADE"), nullable=True)

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    parent: Mapped["AdminDocFolder | None"] = relationship(
        "AdminDocFolder", remote_side=[id], lazy="selectin", back_populates="children"
    )
    children: Mapped[list["AdminDocFolder"]] = relationship(
        "AdminDocFolder",
        cascade="all, delete-orphan",
        lazy="selectin",
        back_populates="parent",
    )
    documents: Mapped[list["AdminDocFile"]] = relationship(
        "AdminDocFile", back_populates="folder", cascade="all, delete-orphan", lazy="selectin"
    )


class AdminDocFile(Base):
    __tablename__ = "admin_doc_files"
    __table_args__ = (
        Index("idx_admin_doc_files_folder", "folder_id"),
        Index("idx_admin_doc_files_library", "library_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    library_key: Mapped[str] = mapped_column(String(64), nullable=False)
    folder_id: Mapped[int | None] = mapped_column(ForeignKey("admin_doc_folders.id", ondelete="SET NULL"), nullable=True)

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    folder: Mapped["AdminDocFolder | None"] = relationship("AdminDocFolder", back_populates="documents", lazy="selectin")
