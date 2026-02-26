import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from app.config import get_settings
from app.models import ExtractTextResponse, OCRResult
from app.ocr_service import OCRService

settings = get_settings()


def combine_texts_conditionally(results: list) -> str:
    """
    Combine texts from multiple images with conditional line breaks.
    
    Only add paragraph break (\n\n) if previous text ends with sentence-ending
    punctuation (.!?). Otherwise, join with a space.
    
    Args:
        results: List of result dicts with 'text' key
        
    Returns:
        Combined text string
    """
    combined_parts = []
    sentence_enders = '.!?'
    
    for i, result in enumerate(results):
        text = result["text"].strip()
        
        if not text:
            continue
            
        if i == 0:
            # First image - just add the text
            combined_parts.append(text)
        else:
            # Check if previous text ends with sentence-ending punctuation
            prev_text = results[i - 1]["text"].strip()
            
            if prev_text and prev_text[-1] in sentence_enders:
                # Previous text ended with punctuation - add paragraph break
                combined_parts.append(text)
            else:
                # Previous text didn't end with punctuation - likely continuation
                # Join with space instead of paragraph break
                if combined_parts:
                    combined_parts[-1] = combined_parts[-1] + " " + text
                else:
                    combined_parts.append(text)
    
    return "\n\n".join(combined_parts)

app = FastAPI(
    title="PhotoToText API",
    description="Extract text from images using Azure OCR",
    version="1.0.0"
)

# CORS configuration
origins = settings.ALLOWED_ORIGINS.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OCR service
ocr_service = OCRService()


def validate_file(file: UploadFile) -> bool:
    """Validate file type and size."""
    # Check extension
    filename = file.filename.lower()
    ext = filename.split('.')[-1] if '.' in filename else ''
    
    if ext not in settings.ALLOWED_EXTENSIONS:
        return False
    
    return True


@app.post("/extract-text", response_model=ExtractTextResponse)
async def extract_text(files: List[UploadFile] = File(...)):
    """
    Extract text from uploaded images.
    
    - Accepts multiple image files
    - Maintains upload order
    - Returns cleaned text with proper line breaks
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 files allowed")
    
    # Validate files
    for file in files:
        if not validate_file(file):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type: {file.filename}. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )
    
    try:
        # Read all files
        images = []
        for file in files:
            content = await file.read()
            
            # Check file size
            if len(content) > settings.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} exceeds maximum size of 10MB"
                )
            
            images.append((content, file.filename))
        
        # Process images with OCR
        results = ocr_service.extract_text_from_multiple_images(images)
        
        # Create combined text with conditional line breaks
        combined_text = combine_texts_conditionally(results)
        
        # Convert to response model
        ocr_results = [
            OCRResult(filename=r["filename"], text=r["text"], order=r["order"])
            for r in results
        ]
        
        return ExtractTextResponse(
            results=ocr_results,
            combined_text=combined_text,
            success=True,
            message=f"Successfully processed {len(results)} image(s)"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "photototext"}


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "message": "PhotoToText API",
        "version": "1.0.0",
        "endpoints": {
            "extract_text": "POST /extract-text",
            "health": "GET /health"
        }
    }