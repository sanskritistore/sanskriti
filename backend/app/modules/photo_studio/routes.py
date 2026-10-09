# -*- coding: utf-8 -*-
"""फ़ोटो स्टूडियो राउटर — photo सुंदर बनाओ endpoint।

POST /photo-studio/enhance
  body: {"image": dataURI, "text": "वैकल्पिक लिखावट"}
  जवाब: {"image": enhancedDataURI}
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_current_tenant_id
from app.modules.photo_studio.service import enhance_photo

router = APIRouter()


class EnhanceRequest(BaseModel):
    """photo सुंदर बनाने की request।"""

    image: str = Field(..., description="data URI या base64 photo")
    text: str | None = Field(None, max_length=60, description="नीचे पट्टी की लिखावट (वैकल्पिक)")


class EnhanceResponse(BaseModel):
    image: str


@router.post("/enhance", response_model=EnhanceResponse)
async def enhance(
    payload: EnhanceRequest,
    _tenant_id: int = Depends(get_current_tenant_id),
):
    """साधारण photo → white background studio photo।

    30-60 सेकंड लग सकते हैं (free server) — frontend धैर्य से इंतज़ार करे।
    """
    try:
        result = await enhance_photo(payload.image, payload.text)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"photo सुंदर नहीं बन पाई: {exc.__class__.__name__} — दूसरी photo आज़माएँ",
        ) from exc
    return EnhanceResponse(image=result)
