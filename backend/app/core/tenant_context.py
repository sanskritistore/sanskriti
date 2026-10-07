"""
टेनेंट कॉन्टेक्स्ट - हर रिक्वेस्ट के लिए वर्तमान टेनेंट

ARCHITECTURE RULE: हर रिक्वेस्ट एक टेनेंट (व्यवसाय) से संबंधित होती है।
JWT टोकन से tenant_id निकालकर request scope में रखा जाता है,
ताकि हर क्वेरी अपने ही टेनेंट का डेटा देखे।
"""

import asyncio
from contextvars import ContextVar
from typing import Optional

# वर्तमान टेनेंट का context variable (async-safe)
_current_tenant_id: ContextVar[Optional[int]] = ContextVar(
    "current_tenant_id", default=None
)


def set_current_tenant(tenant_id: int) -> None:
    """वर्तमान रिक्वेस्ट का टेनेंट सेट करें।"""
    _current_tenant_id.set(tenant_id)


def get_current_tenant_id() -> Optional[int]:
    """वर्तमान टेनेंट ID लौटाएँ (यदि सेट नहीं, None)।"""
    return _current_tenant_id.get()


def clear_current_tenant() -> None:
    """टेनेंट कॉन्टेक्स्ट साफ़ करें।"""
    _current_tenant_id.set(None)
