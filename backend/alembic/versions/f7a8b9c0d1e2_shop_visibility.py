"""products.show_in_shop — दुकान page पर कौन सा item दिखे, मालिक चुने

10-10 user सवाल: "shop link में सारे items दिखें या main-main?"
जवाब: मालिक जो चुने वही। डिफ़ॉल्ट True (पुराने products दिखते रहें)।

Revision ID: f7a8b9c0d1e2
Revises: e5b6c3d8a9f1
"""

from alembic import op
import sqlalchemy as sa

revision = "f7a8b9c0d1e2"
down_revision = "e5b6c3d8a9f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "show_in_shop",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("products", "show_in_shop")
