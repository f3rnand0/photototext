import os
import time
import logging
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from app.config import get_settings
from app.models import ExtractTextResponse, OCRResult
from app.ocr_service import OCRService
from app.logger import get_logger, set_request_id, clear_request_id, log_execution_time

settings = get_settings()
logger = get_logger("main")

# Initialize Sentry if DSN is provided
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            FastApiIntegration(),
            LoggingIntegration(
                level=logging.DEBUG if settings.DEBUG else logging.INFO,
                event_level=logging.ERROR
            ),
        ],
        traces_sample_rate=1.0 if settings.DEBUG else 0.1,
        profiles_sample_rate=1.0 if settings.DEBUG else 0.1,
        environment="development" if settings.DEBUG else "production",
    )
    logger.info("Sentry initialized successfully")
else:
    logger.info("Sentry DSN not provided, skipping initialization")

app = FastAPI(
    title="PhotoToText API",
    description="Extract text from images using Azure OCR",
    version="1.0.0"
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Set request ID from header or generate new one
    request_id = request.headers.get("X-Request-ID", "")
    request_id = set_request_id(request_id if request_id else None)
    
    start_time = time.time()
    
    logger.info(
        f"Request started: {request.method} {request.url.path}",
        extra={"context": {"client_ip": request.client.host if request.client else "unknown"}}
    )
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        logger.info(
            f"Request completed: {request.method} {request.url.path}",
            extra={"context": {
                "status_code": response.status_code,
                "duration_seconds": f"{duration:.3f}"
            }}
        )
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"Request failed: {request.method} {request.url.path}",
            exc_info=True,
            extra={"context": {
                "duration_seconds": f"{duration:.3f}",
                "error": str(e)
            }}
        )
        raise
    finally:
        clear_request_id()


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
    logger.info(f"Extract text endpoint called with {len(files)} files")
    
    if not files:
        logger.warning("No files provided in request")
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    if len(files) > 20:
        logger.warning(f"Too many files: {len(files)} (max 20)")
        raise HTTPException(status_code=400, detail="Maximum 20 files allowed")
    
    # Validate files
    for file in files:
        if not validate_file(file):
            logger.warning(f"Invalid file type rejected: {file.filename}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type: {file.filename}. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )
    
    try:
        # Read all files
        images = []
        total_size = 0
        
        logger.info("Reading uploaded files")
        for file in files:
            content = await file.read()
            total_size += len(content)
            
            logger.debug(f"File read: {file.filename} ({len(content)} bytes)")
            
            # Check file size
            if len(content) > settings.MAX_FILE_SIZE:
                logger.warning(f"File too large: {file.filename} ({len(content)} bytes)")
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} exceeds maximum size of 10MB"
                )
            
            images.append((content, file.filename))
        
        logger.info(f"All files read successfully", extra={"context": {
            "file_count": len(images),
            "total_size_bytes": total_size,
            "filenames": [img[1] for img in images]
        }})
        
        # Process images with OCR
        logger.info("Starting OCR processing")
        results = ocr_service.extract_text_from_multiple_images(images)
        
        # Create combined text with conditional line breaks
        combined_text = combine_texts_conditionally(results)
        
        # Calculate stats
        success_count = sum(1 for r in results if not r["text"].startswith("Error:"))
        error_count = len(results) - success_count
        total_chars = sum(len(r["text"]) for r in results)
        
        logger.info("OCR processing completed", extra={"context": {
            "total_files": len(results),
            "success_count": success_count,
            "error_count": error_count,
            "total_chars": total_chars,
            "combined_text_length": len(combined_text)
        }})
        
        # Convert to response model
        ocr_results = [
            OCRResult(filename=r["filename"], text=r["text"], order=r["order"])
            for r in results
        ]
        
        return ExtractTextResponse(
            results=ocr_results,
            combined_text=combined_text,
            success=True,
            message=f"Successfully processed {success_count} image(s)"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Processing error occurred", exc_info=True, extra={"context": {
            "error": str(e),
            "file_count": len(files)
        }})
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