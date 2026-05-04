import os
import time
import io
from typing import List, Tuple
from PIL import Image
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials

from app.config import get_settings
from app.text_processor import process_extracted_text
from app.logger import get_logger

logger = get_logger("ocr_service")

MAX_DIMENSION = 2000
JPEG_QUALITY = 85

def compress_image(image_bytes: bytes, filename: str) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    original_size = len(image_bytes)

    if max(img.size) > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

    output = io.BytesIO()
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.save(output, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    compressed = output.getvalue()

    logger.info(f"Image compressed", extra={"context": {
        "filename": filename,
        "original_size_bytes": original_size,
        "compressed_size_bytes": len(compressed),
        "original_dimensions": f"{img.width}x{img.height}"
    }})

    return compressed


class OCRService:
    def __init__(self):
        settings = get_settings()
        self.client = ComputerVisionClient(
            endpoint=settings.AZURE_OCR_ENDPOINT,
            credentials=CognitiveServicesCredentials(settings.AZURE_OCR_KEY)
        )

    def extract_text_from_image(self, image_bytes: bytes, filename: str) -> str:
        logger.info(f"OCR processing started for {filename}", extra={"context": {
            "filename": filename,
            "image_size_bytes": len(image_bytes)
        }})

        start_time = time.time()

        try:
            image_bytes = compress_image(image_bytes, filename)

            logger.debug(f"Calling Azure Read API for {filename}")
            api_start = time.time()

            read_response = self.client.read_in_stream(
                io.BytesIO(image_bytes),
                raw=True
            )

            operation_location = read_response.headers["Operation-Location"]
            operation_id = operation_location.split("/")[-1]

            logger.debug(f"Azure operation started", extra={"context": {
                "filename": filename,
                "operation_id": operation_id
            }})

            poll_count = 0
            while True:
                read_result = self.client.get_read_result(operation_id)
                poll_count += 1

                if read_result.status not in ['notStarted', 'running']:
                    break

                if poll_count > 100:
                    raise Exception("OCR operation timeout after 100 polls")

                time.sleep(3)

            api_duration = time.time() - api_start

            logger.info(f"Azure OCR completed for {filename}", extra={"context": {
                "filename": filename,
                "operation_status": str(read_result.status),
                "api_duration_seconds": f"{api_duration:.2f}"
            }})

            if read_result.status == OperationStatusCodes.succeeded:
                lines_with_boxes = []

                for text_result in read_result.analyze_result.read_results:
                    for line in text_result.lines:
                        lines_with_boxes.append({
                            'text': line.text,
                            'bounding_box': line.bounding_box
                        })

                logger.debug(f"Raw text extracted", extra={"context": {
                    "filename": filename,
                    "raw_lines_count": len(lines_with_boxes)
                }})

                process_start = time.time()
                cleaned_text = process_extracted_text(lines_with_boxes)
                process_duration = time.time() - process_start

                total_duration = time.time() - start_time

                logger.info(f"OCR processing finished for {filename}", extra={"context": {
                    "filename": filename,
                    "raw_lines": len(lines_with_boxes),
                    "cleaned_text_length": len(cleaned_text),
                    "processing_duration_seconds": f"{process_duration:.2f}",
                    "total_duration_seconds": f"{total_duration:.2f}"
                }})

                return cleaned_text
            else:
                error_msg = f"OCR operation failed with status: {read_result.status}"
                logger.error(error_msg, extra={"context": {
                    "filename": filename,
                    "operation_id": operation_id,
                    "status": str(read_result.status)
                }})
                raise Exception(error_msg)

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"OCR processing failed for {filename}", exc_info=True, extra={"context": {
                "filename": filename,
                "image_size_bytes": len(image_bytes),
                "duration_seconds": f"{duration:.2f}",
                "error": str(e)
            }})
            raise Exception(f"Error processing {filename}: {str(e)}")

    def extract_text_from_multiple_images(
        self,
        images: List[Tuple[bytes, str]]
    ) -> List[dict]:
        logger.info(f"Starting batch OCR processing", extra={"context": {
            "total_images": len(images),
            "filenames": [img[1] for img in images]
        }})

        results = []
        success_count = 0
        error_count = 0

        for idx, (image_bytes, filename) in enumerate(images):
            logger.info(f"Batch image {idx + 1}/{len(images)} started: {filename}")

            try:
                text = self.extract_text_from_image(image_bytes, filename)
                results.append({
                    "filename": filename,
                    "text": text,
                    "order": idx
                })
                success_count += 1
                logger.info(f"Batch image {idx + 1}/{len(images)} completed: {filename}")

            except Exception as e:
                error_msg = f"Error: {str(e)}"
                results.append({
                    "filename": filename,
                    "text": error_msg,
                    "order": idx
                })
                error_count += 1
                logger.error(f"Batch image {idx + 1}/{len(images)} failed: {filename}", extra={"context": {
                    "filename": filename,
                    "order": idx,
                    "error": str(e)
                }})

        logger.info(f"Batch OCR processing completed", extra={"context": {
            "total_images": len(images),
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": f"{(success_count/len(images)*100):.1f}%"
        }})

        return results
