"""Create leads table for manual Lead Finder review.

Revision ID: 20260911_0005
Revises: 20260909_0004
Create Date: 2026-09-11
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260911_0005"
down_revision: str | None = "20260909_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "leads",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("niche", sa.String(length=32), nullable=False),
        sa.Column("contact", sa.String(length=255), nullable=False),
        sa.Column("reason_fit", sa.Text(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="new", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "niche IN ('smm', 'designers', 'photographers', 'bloggers', "
            "'small_business', 'online_stores')",
            name="ck_leads_niche",
        ),
        sa.CheckConstraint("score >= 0 AND score <= 100", name="ck_leads_score_range"),
        sa.CheckConstraint(
            "status IN ('new', 'contacted', 'interested', 'rejected')",
            name="ck_leads_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "url", name="uq_leads_source_url"),
    )
    op.create_index("ix_leads_niche", "leads", ["niche"])
    op.create_index(
        "ix_leads_status_score_created",
        "leads",
        ["status", "score", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_leads_status_score_created", table_name="leads")
    op.drop_index("ix_leads_niche", table_name="leads")
    op.drop_table("leads")
