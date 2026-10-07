"""
सभी मॉडल एक जगह - alembic और Base.metadata के लिए आवश्यक।

नया मॉडल बनाने पर उसे यहाँ import करना आवश्यक है,
ताकि alembic migrations उसे पकड़ सकें।
"""

from app.core.database import Base
from app.models.tenant import Tenant, User
from app.models.product import Product, ProductPhoto
from app.models.campaign import Campaign, PlatformCampaign, AdCreative
from app.models.payment import WalletTransaction, Lead
from app.models.otp import OtpCode

__all__ = [
    "Base",
    "Tenant",
    "User",
    "Product",
    "ProductPhoto",
    "Campaign",
    "PlatformCampaign",
    "AdCreative",
    "WalletTransaction",
    "Lead",
    "OtpCode",
]
