"""product_photos.url → TEXT (base64 photos VARCHAR(512) से बड़ी हैं)

Revision ID: c9e4f1a2b3d5
Revises: b7f2a1c9d3e4
Create Date: 2026-10-07
"""
from alembic import op
import sqlalchemy as sa

revision = "c9e4f1a2b3d5"
down_revision = "b7f2a1c9d3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "product_photos",
        "url",
        existing_type=sa.String(length=512),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "product_photos",
        "url",
        existing_type=sa.Text(),
        type_=sa.String(length=512),
        existing_nullable=False,
    )
