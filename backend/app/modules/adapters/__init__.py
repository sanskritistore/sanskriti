"""
एडाप्टर रजिस्ट्री - प्लेटफॉर्म नाम से एडाप्टर देता है

नया प्लेटफॉर्म जोड़ने के लिए:
1. नया एडाप्टर बनाएँ (BasePlatformAdapter उत्तराधिकारी)
2. नीचे _ADAPTERS में नाम → क्लास जोड़ें
बस! runner अपने-आप नए प्लेटफॉर्म को चला लेगा।
"""

from typing import Dict, Type

from app.modules.adapters.base import BasePlatformAdapter, CampaignConfig
from app.modules.adapters.meta_adapter import MetaAdapter

# प्लेटफॉर्म रजिस्ट्री - नाम → एडाप्टर क्लास
_ADAPTERS: Dict[str, Type[BasePlatformAdapter]] = {
    "meta": MetaAdapter,
    # "google": GoogleAdapter,  # भविष्य में
}


def get_adapter(platform: str) -> BasePlatformAdapter:
    """प्लेटफॉर्म नाम से एडाप्टर इंस्टेंस देता है।"""
    adapter_cls = _ADAPTERS.get(platform)
    if adapter_cls is None:
        from app.core.exceptions import AdapterError
        raise AdapterError(platform, "असमर्थित प्लेटफॉर्म - एडाप्टर नहीं मिला")
    return adapter_cls()


def supported_platforms() -> list[str]:
    """समर्थित प्लेटफॉर्मों के नाम।"""
    return list(_ADAPTERS.keys())


__all__ = [
    "BasePlatformAdapter",
    "CampaignConfig",
    "MetaAdapter",
    "get_adapter",
    "supported_platforms",
]
