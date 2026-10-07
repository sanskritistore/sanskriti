"""पहले pilot ग्राहक (CSC Print Cafe, 9873152325) को ₹500 testing credit

Revision ID: d1a5e2b4c6f7
Revises: c9e4f1a2b3d5
Create Date: 2026-10-07

पैसा असली Meta account में पहले से है (~₹172); यह सिर्फ़ हमारे
software के अंदरूनी wallet ledger को pilot test के लिए sync करता है।
"""
from alembic import op

revision = "d1a5e2b4c6f7"
down_revision = "c9e4f1a2b3d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE tenants SET wallet_balance = 500 WHERE phone = '9873152325'"
    )


def downgrade() -> None:
    pass
