"""platform chain ids (adset/creative/ad)

Revision ID: b7f2a1c9d3e4
Revises: e36228319487
Create Date: 2026-10-06

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7f2a1c9d3e4"
down_revision = "e36228319487"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "platform_campaigns",
        sa.Column("platform_adset_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "platform_campaigns",
        sa.Column("platform_creative_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "platform_campaigns",
        sa.Column("platform_ad_id", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("platform_campaigns", "platform_ad_id")
    op.drop_column("platform_campaigns", "platform_creative_id")
    op.drop_column("platform_campaigns", "platform_adset_id")
