"""
i18n सर्विस - भाषा और अनुवाद प्रबंधन

संस्कृति की भाषाएँ: हिंदी, अंग्रेज़ी, मराठी, गुजराती,
बंगाली, तमिल, तेलुगु (MVP में)।

संरचना: अनुवाद dict में रखे गए हैं; बाद में DB/फ़ाइल में जा सकते हैं।
"""

from app.core.config import settings

# भाषा कोड → भाषा का नाम (स्थानीय लिपि में)
LANGUAGES = {
    "hi": "हिंदी",
    "en": "English",
    "mr": "मराठी",
    "gu": "ગુજરાતી",
    "bn": "বাংলা",
    "ta": "தமிழ்",
    "te": "తెలుగు",
}

# मूल अनुवाद (हिंदी आधार) - MVP स्टब
# TODO: पूर्ण अनुवाद फ़ाइलों में ले जाएँ (locales/hi.json आदि)
_TRANSLATIONS: dict[str, dict[str, str]] = {
    "hi": {
        "welcome": "संस्कृति में आपका स्वागत है",
        "create_ad": "विज्ञापन बनाएँ",
        "launch_campaign": "कैंपेन लॉन्च करें",
        "wallet_balance": "वॉलेट बैलेंस",
        "recharge": "रिचार्ज करें",
        "reports": "रिपोर्ट",
        "insufficient_budget": "अपर्याप्त बजट - कृपया वॉलेट रिचार्ज करें",
    },
    "en": {
        "welcome": "Welcome to Sanskriti",
        "create_ad": "Create Ad",
        "launch_campaign": "Launch Campaign",
        "wallet_balance": "Wallet Balance",
        "recharge": "Recharge",
        "reports": "Reports",
        "insufficient_budget": "Insufficient budget - please recharge wallet",
    },
}


def get_supported_languages() -> dict:
    """समर्थित भाषाओं की सूची (कोड + नाम)।"""
    return {
        "languages": [
            {"code": code, "name": name} for code, name in LANGUAGES.items()
        ],
        "default": "hi",
    }


def get_translations(lang: str) -> dict:
    """किसी भाषा के अनुवाद लौटाएँ (न मिले तो हिंदी)।"""
    if lang not in LANGUAGES:
        from fastapi import HTTPException, status
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"भाषा समर्थित नहीं: {lang}",
        )
    # अनुवाद उपलब्ध न हो तो हिंदी fallback
    return _TRANSLATIONS.get(lang, _TRANSLATIONS["hi"])
