from pydantic import BaseModel
from typing import List, Optional


class OCRResult(BaseModel):
    filename: str
    text: str
    order: int


class ExtractTextResponse(BaseModel):
    results: List[OCRResult]
    combined_text: str
    success: bool
    message: str


class ErrorResponse(BaseModel):
    detail: str