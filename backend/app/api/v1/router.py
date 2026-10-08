"""
API v1 राउटर - सभी मॉड्यूल के राउटर यहाँ जुड़ते हैं।

प्रत्येक मॉड्यूल का राउटर अपने-आप में encapsulated है।
नया मॉड्यूल जोड़ने के लिए: router.include_router(<module>.router)

प्रीफ़िक्स फ्रंटएंड lib/api.js के कॉन्ट्रैक्ट से मेल खाते हैं:
/auth/*, /business, /products, /ads, /reports/summary
"""

from fastapi import APIRouter

from app.modules.auth.routes import router as auth_router
from app.modules.tenant.routes import router as tenant_router
from app.modules.product.routes import router as product_router
from app.modules.ads.routes import router as ads_router
from app.modules.ad_studio.routes import router as ad_studio_router
from app.modules.runner.routes import router as runner_router
from app.modules.reports.routes import router as reports_router
from app.modules.payments.routes import router as payments_router
from app.modules.i18n.routes import router as i18n_router
from app.modules.targeting.routes import router as targeting_router
from app.modules.billing.routes import router as billing_router
from app.modules.whatsapp.routes import router as whatsapp_router

api_router = APIRouter()

# सभी मॉड्यूल राउटर जोड़ें
# प्रमाणीकरण (pre-auth - इस पर tenant dependency नहीं)
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
# व्यवसाय प्रोफ़ाइल (फ्रंटएंड "business" कहता है, मॉड्यूल "tenant" है)
api_router.include_router(tenant_router, prefix="/business", tags=["business"])
api_router.include_router(product_router, prefix="/products", tags=["products"])
# फ्रंटएंड का सरल ad कॉन्ट्रैक्ट (कैंपेन लेयर 1 पर पतला मुखौटा)
api_router.include_router(ads_router, prefix="/ads", tags=["ads"])
api_router.include_router(ad_studio_router, prefix="/ad-studio", tags=["ad-studio"])
api_router.include_router(runner_router, prefix="/campaigns", tags=["campaigns"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_router.include_router(payments_router, prefix="/payments", tags=["payments"])
api_router.include_router(i18n_router, prefix="/i18n", tags=["i18n"])
api_router.include_router(targeting_router, prefix="/targeting", tags=["targeting"])
api_router.include_router(billing_router, prefix="/billing", tags=["billing"])
api_router.include_router(whatsapp_router, prefix="/whatsapp", tags=["whatsapp"])
