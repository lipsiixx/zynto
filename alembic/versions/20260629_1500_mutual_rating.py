"""mutual_rating table

Revision ID: mutual_rating
Revises: contact_trust
Create Date: 2026-06-29 15:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "mutual_rating"
down_revision = "contact_trust"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mutual_rating",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("requester_id", sa.BigInteger(), nullable=False),
        sa.Column("target_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("requester_score", sa.Integer(), nullable=True),
        sa.Column("target_score", sa.Integer(), nullable=True),
        sa.Column("mutual_score", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mutual_rating_pair", "mutual_rating", ["requester_id", "target_id"], unique=True)
    op.create_index("ix_mutual_rating_target", "mutual_rating", ["target_id"])


def downgrade() -> None:
    op.drop_index("ix_mutual_rating_target", table_name="mutual_rating")
    op.drop_index("ix_mutual_rating_pair", table_name="mutual_rating")
    op.drop_table("mutual_rating")
