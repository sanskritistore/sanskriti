"""
कस्टम एक्सेप्शन - त्रुटियाँ

सभी बिज़नेस-लॉजिक त्रुटिएँ इन क्लासेस से आती हैं,
जिन्हें API स्तर पर साफ़ HTTP उत्तर में बदला जाता है।
"""

from fastapi import HTTPException, status


class SanskritiException(HTTPException):
    """सभी कस्टम त्रुटियों का आधार।"""

    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class TenantNotFoundError(SanskritiException):
    """टेनेंट (व्यवसाय) नहीं मिला।"""

    def __init__(self, tenant_id=None):
        detail = f"टेनेंट नहीं मिला (id: {tenant_id})" if tenant_id else "टेनेंट नहीं मिला"
        super().__init__(status.HTTP_404_NOT_FOUND, detail)


class ProductNotFoundError(SanskritiException):
    """उत्पाद नहीं मिला।"""

    def __init__(self, product_id=None):
        detail = f"उत्पाद नहीं मिला (id: {product_id})" if product_id else "उत्पाद नहीं मिला"
        super().__init__(status.HTTP_404_NOT_FOUND, detail)


class CampaignNotFoundError(SanskritiException):
    """कैंपेन नहीं मिली।"""

    def __init__(self, campaign_id=None):
        detail = f"कैंपेन नहीं मिली (id: {campaign_id})" if campaign_id else "कैंपेन नहीं मिली"
        super().__init__(status.HTTP_404_NOT_FOUND, detail)


class CampaignNotDraftError(SanskritiException):
    """सिर्फ़ draft कैंपेन मिट सकती है — active/paused पर इनकार।"""

    def __init__(self, campaign_id=None):
        super().__init__(
            status.HTTP_400_BAD_REQUEST,
            f"सिर्फ़ रुकी हुई (draft) कैंपेन मिट सकती है (id: {campaign_id}) — पहले ⏸ रोकें",
        )


class CampaignNotLinkedError(SanskritiException):
    """कैंपेन का Meta से link नहीं (पुरानी legacy कैंपेन) — app से रोक/चालू नहीं हो सकती।

    10-10 bug: पुरानी कैंपेन में PlatformCampaign row नहीं था, pause ने
    चुपचाप सिर्फ़ DB बदला — Meta पर ad चलती रही और पैसा कटता रहा!
    Silent failure पर पैसा खर्च होता है — इसलिए साफ़ error दिखाओ।
    """

    def __init__(self, campaign_id=None):
        super().__init__(
            status.HTTP_409_CONFLICT,
            f"यह पुरानी ad है — Meta से link नहीं मिला (id: {campaign_id})। "
            "app से रोक/चालू नहीं होगी। कृपया support को बताएँ — Meta पर सीधे रोकी जाएगी।",
        )


class InsufficientBudgetError(SanskritiException):
    """वॉलेट में पर्याप्त बजट नहीं है।"""

    def __init__(self, required: float = None, available: float = None):
        detail = (
            f"अपर्याप्त बजट - आवश्यक: ₹{required}, उपलब्ध: ₹{available}"
            if required is not None
            else "अपर्याप्त बजट"
        )
        super().__init__(status.HTTP_402_PAYMENT_REQUIRED, detail)


class AdapterError(SanskritiException):
    """प्लेटफॉर्म एडाप्टर त्रुटि (Meta/Google आदि)।"""

    def __init__(self, platform: str, message: str):
        super().__init__(
            status.HTTP_502_BAD_GATEWAY,
            f"प्लेटफॉर्म '{platform}' त्रुटि: {message}",
        )


class PaymentError(SanskritiException):
    """भुगतान त्रुटि (UPI/रेज़रपे)।"""

    def __init__(self, message: str):
        super().__init__(status.HTTP_400_BAD_REQUEST, f"भुगतान त्रुटि: {message}")
