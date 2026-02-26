import os
import time
import io
from typing import List, Tuple
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials

from app.config import get_settings
from app.text_processor import process_extracted_text


class OCRService:
    def __init__(self):
        settings = get_settings()
        self.client = ComputerVisionClient(
            endpoint=settings.AZURE_OCR_ENDPOINT,
            credentials=CognitiveServicesCredentials(settings.AZURE_OCR_KEY)
        )
    
    def extract_text_from_image(self, image_bytes: bytes, filename: str) -> str:
        """
        Extract text from image using Azure Read API.
        Returns cleaned text with proper line breaks.
        """
        try:
            # Call Read API
            read_response = self.client.read_in_stream(
                io.BytesIO(image_bytes),
                raw=True
            )
            
            # Get operation location (ID)
            operation_location = read_response.headers["Operation-Location"]
            operation_id = operation_location.split("/")[-1]
            
            # Wait for the operation to complete
            while True:
                read_result = self.client.get_read_result(operation_id)
                if read_result.status not in ['notStarted', 'running']:
                    break
                time.sleep(1)
            
            # Extract text from results with bounding boxes
            if read_result.status == OperationStatusCodes.succeeded:
                lines_with_boxes = []
                
                for text_result in read_result.analyze_result.read_results:
                    for line in text_result.lines:
                        lines_with_boxes.append({
                            'text': line.text,
                            'bounding_box': line.bounding_box
                        })
                
                # Process text with new pipeline
                cleaned_text = process_extracted_text(lines_with_boxes)
                
                return cleaned_text
            else:
                raise Exception(f"OCR operation failed with status: {read_result.status}")
                
        except Exception as e:
            raise Exception(f"Error processing {filename}: {str(e)}")
    
    def extract_text_from_multiple_images(
        self, 
        images: List[Tuple[bytes, str]]
    ) -> List[dict]:
        """
        Extract text from multiple images maintaining order.
        
        Args:
            images: List of tuples (image_bytes, filename)
        
        Returns:
            List of dicts with filename, text, and order
        """
        results = []
        
        for idx, (image_bytes, filename) in enumerate(images):
            try:
                text = self.extract_text_from_image(image_bytes, filename)
                results.append({
                    "filename": filename,
                    "text": text,
                    "order": idx
                })
            except Exception as e:
                results.append({
                    "filename": filename,
                    "text": f"Error: {str(e)}",
                    "order": idx
                })
        
        return results
