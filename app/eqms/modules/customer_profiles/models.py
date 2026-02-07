from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.eqms.models import Base


class Rep(Base):
    """
    Simple rep entity for assignment tracking.
    Reps do NOT log into the system - they are just names/identifiers.
    """
    __tablename__ = "reps"
    __table_args__ = (
        Index("idx_reps_name", "name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    territory: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)

    customer_assignments: Mapped[list["CustomerRep"]] = relationship(
        "CustomerRep",
        back_populates="rep",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        Index("idx_customers_company_key", "company_key"),
        Index("idx_customers_facility_name", "facility_name"),
        Index("idx_customers_state", "state"),
        Index("idx_customers_primary_rep_id", "primary_rep_id"),
        Index("idx_customers_customer_code", "customer_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    customer_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    facility_name: Mapped[str] = mapped_column(Text, nullable=False)

    address1: Mapped[str | None] = mapped_column(Text, nullable=True)
    address2: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str | None] = mapped_column(Text, nullable=True)
    zip: Mapped[str | None] = mapped_column(Text, nullable=True)

    contact_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(Text, nullable=True)

    primary_rep_id: Mapped[int | None] = mapped_column(ForeignKey("reps.id", ondelete="SET NULL"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)

    primary_rep = relationship("Rep", foreign_keys=[primary_rep_id], lazy="selectin")
    notes: Mapped[list["CustomerNote"]] = relationship(
        "CustomerNote",
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    rep_assignments: Mapped[list["CustomerRep"]] = relationship(
        "CustomerRep",
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CustomerNote(Base):
    __tablename__ = "customer_notes"
    __table_args__ = (
        Index("idx_customer_notes_customer_id", "customer_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)

    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    note_date: Mapped[date | None] = mapped_column(Date, nullable=True, default=date.today)
    author: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)

    customer: Mapped[Customer] = relationship("Customer", back_populates="notes", lazy="selectin")


class CustomerRep(Base):
    __tablename__ = "customer_reps"
    __table_args__ = (
        Index("idx_customer_reps_customer_id", "customer_id"),
        Index("idx_customer_reps_rep_id", "rep_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    rep_id: Mapped[int] = mapped_column(ForeignKey("reps.id", ondelete="CASCADE"), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    customer: Mapped[Customer] = relationship("Customer", back_populates="rep_assignments", lazy="selectin")
    rep = relationship("Rep", foreign_keys=[rep_id], lazy="selectin")

