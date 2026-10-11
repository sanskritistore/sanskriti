"""
स्टोर ऑर्डर मॉडल — customer के फोटो फ्रेम ऑर्डर।

11-10 user pipeline: customer site पर फोटो set करता है → submit →
4K print file backend में आती है → admin (print team) download करके
print + acrylic + hanging → dispatch।
"""

from sqlalchemy import BigInteger, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantMixin, TimestampMixin


class StoreOrder(Base, TenantMixin, TimestampMixin):
    """एक customer ऑर्डर — print file + customer details + status."""

    __tablename__ = "store_orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, comment="ऑर्डर नंबर जैसे SS-00012"
    )

    # customer
    customer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    customer_address: Mapped[str | None] = mapped_column(Text, nullable=True)

    # item (frame)
    frame_id: Mapped[str] = mapped_column(String(40), nullable=False)
    frame_name: Mapped[str] = mapped_column(String(120), nullable=False)
    ratio: Mapped[str] = mapped_column(String(8), nullable=False, default="2:3")
    size_label: Mapped[str] = mapped_column(String(40), nullable=False)
    size_w: Mapped[int] = mapped_column(Integer, nullable=False, comment="इंच में चौड़ाई")
    size_h: Mapped[int] = mapped_column(Integer, nullable=False, comment="इंच में ऊँचाई")
    thickness_mm: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    price: Mapped[int] = mapped_column(Integer, nullable=False)

    # customer ने photo कैसे set की (zoom/move/rotate + DPI) — JSON text
    settings: Mapped[str | None] = mapped_column(Text, nullable=True)

    # files (disk पर path)
    print_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    preview_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # bytes DB में — disk ephemeral है (11-10)
    print_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    preview_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    # pipeline status: new → printed → ready → dispatched → done (cancelled अलग)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new", index=True)
