"""
i18n राउटर - भाषा और अनुवाद एंडपॉइंट

समर्थित भाषाएँ और अनुवाद लौटाता है।
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_tenant_id
from app.modules.i18n import service

router = APIRouter()


@router.get("/languages")
async def list_languages(
    tenant_id: int = Depends(get_current_tenant_id),
):
    """समर्थित भाषाओं की सूची।"""
    return service.get_supported_languages()


@router.get("/translations/{lang}")
async def get_translations(
    lang: str,
    tenant_id: int = Depends(get_current_tenant_id),
):
    """किसी भाषा के सभी अनुवाद लौटाएँ।"""
    return service.get_translations(lang)
