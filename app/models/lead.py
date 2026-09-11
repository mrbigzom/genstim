from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="ck_leads_score_range"),
        CheckConstraint(
            "status IN ('new', 'contacted', 'interested', 'rejected')",
            name="ck_leads_status",
        ),
        CheckConstraint(
            "niche IN ('smm', 'designers', 'photographers', 'bloggers', "
            "'small_business', 'online_stores')",
            name="ck_leads_niche",
        ),
        UniqueConstraint("source", "url", name="uq_leads_source_url"),
        Index("ix_leads_status_score_created", "status", "score", "created_at"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    niche: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    contact: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    reason_fit: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="new",
        server_default="new",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
