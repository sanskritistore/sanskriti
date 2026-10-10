"""carousel items + tenant google rating (10-10 user माँग)

Revision ID: e5b6c3d8a9f1
Revises: d1a5e2b4c6f7
Create Date: 2026-10-10

User idea (10-10 सुबह): ad पर click/swipe करने से कई posters एक-एक करके
दिखें (Meta carousel) + आख़िरी card में असली Google reviews दिखें ताकि
लोग समझें "fake नहीं है"।
"""
from alembic import op
import sqlalchemy as sa

revision = "e5b6c3d8a9f1"
down_revision = "d1a5e2b4c6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ad creative के साथ कई cards (JSON list: [{image_url, headline}])
    op.add_column("ad_creatives", sa.Column("carousel_items", sa.Text(), nullable=True))
    # Tenant की असली Google rating (review card बनाने के लिए)
    op.add_column("tenants", sa.Column("google_rating", sa.Float(), nullable=True))
    op.add_column("tenants", sa.Column("google_reviews_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "google_reviews_count")
    op.drop_column("tenants", "google_rating")
    op.drop_column("ad_creatives", "carousel_items")
