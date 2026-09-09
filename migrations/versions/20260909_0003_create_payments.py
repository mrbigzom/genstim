"""Create Telegram Stars payments table.

Revision ID: 20260909_0003
Revises: 20260908_0002
Create Date: 2026-09-09
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260909_0003"
down_revision: str | None = "20260908_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("invoice_payload", sa.String(length=128), nullable=False),
        sa.Column("telegram_payment_charge_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("generation_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("service_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refund_charge_id", sa.String(length=255), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["generation_id"], ["generations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("generation_id"),
        sa.UniqueConstraint("invoice_payload"),
        sa.UniqueConstraint("telegram_payment_charge_id"),
    )
    op.create_index("ix_payments_telegram_user_id", "payments", ["telegram_user_id"])
    op.create_index(
        "ix_payments_user_product_status",
        "payments",
        ["user_id", "product_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_payments_user_product_status", table_name="payments")
    op.drop_index("ix_payments_telegram_user_id", table_name="payments")
    op.drop_table("payments")
