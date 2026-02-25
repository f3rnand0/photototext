import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from app.config import get_settings
from app.models import ExtractTextResponse, OCRResult
from app.ocr_service import OCRService

settings = get_settings()

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
        
        # Create combined text
        combined_text = "\n\n".join([r["text"] for r in results])
        
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