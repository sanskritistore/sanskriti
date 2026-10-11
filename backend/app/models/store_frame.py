"""
कस्टम फ्रेम मॉडल — Frame Maker tool से बनाए गए फ्रेम।

11-10 user माँग: "jo frame maine aapko bataye wo kaise banenge" —
owner खुद PNG border upload करके, photo window mark करके,
बिना coding के नया frame बनाए → तुरंत store पर live।
"""

from sqlalchemy import BigInteger, Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantMixin, TimestampMixin


class StoreFrame(Base, TenantMixin, TimestampMixin):
    """एक custom frame — PNG border + photo window + pricing।"""

    __tablename__ = "store_frames"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    frame_id: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, comment="slug जैसे fr-c12"
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    shape: Mapped[str] = mapped_column(
        String(20), nullable=False, default="rect",
        comment="photo window का shape: rect/rounded/oval/circle/heart",
    )
    ratio: Mapped[str] = mapped_column(
        String(8), nullable=False, default="2:3", comment="sizes group: 1:1/2:3/3:2"
    )
    ar: Mapped[str] = mapped_column(
        String(12), nullable=False, default="2/3", comment="PNG की असली aspect (css)"
    )
    base: Mapped[int] = mapped_column(Integer, nullable=False, default=399)
    rating: Mapped[float] = mapped_column(Float, nullable=False, default=4.5)

    img_path: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    # Generator frame (PNG के बिना): border colors/widths + windows (collage)
    draw: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    # photo window — frame के % में: {"x":12,"y":10,"w":76,"h":80}
    window: Mapped[str] = mapped_column(String(200), nullable=False)

    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
