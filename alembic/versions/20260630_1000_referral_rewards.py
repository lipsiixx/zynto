"""referral_rewards table

Revision ID: referral_rewards
Revises: mutual_rating
Create Date: 2026-06-30 10:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "referral_rewards"
down_revision = "mutual_rating"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "referral_rewards",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("referrer_id", sa.BigInteger(), nullable=False),
        sa.Column("referred_id", sa.BigInteger(), nullable=False),
        sa.Column("days_granted", sa.Integer(), nullable=False),
        sa.Column("payment_method", sa.String(20), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_referral_rewards_referrer", "referral_rewards", ["referrer_id"])
    op.create_index("ix_referral_rewards_referred", "referral_rewards", ["referred_id"])


def downgrade() -> None:
    op.drop_index("ix_referral_rewards_referred", table_name="referral_rewards")
    op.drop_index("ix_referral_rewards_referrer", table_name="referral_rewards")
    op.drop_table("referral_rewards")
