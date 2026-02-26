"""
Debug script for margin filtering analysis.

This script analyzes actual Azure OCR output to understand:
1. Where margin text appears (position, coordinates)
2. How the clustering algorithm processes it
3. Why certain text is not being filtered

Usage:
    cd /Users/fernando/ws/photototext/backend
    python debug_margin_filter.py
"""

import sys
sys.path.insert(0, '/Users/fernando/ws/photototext/backend')

from app.text_processor import (
    filter_margin_text_c2,
    cluster_text_boxes,
    extract_box_data,
    is_at_extreme_edge,
    calculate_distance,
    identify_main_content_cluster,
    MARGIN_FILTER_CONFIG
)
from app.ocr_service import OCRService
import io
from pathlib import Path

# Sample data from actual Azure OCR output
# Based on the integration test output showing "Torella", "siativ", etc.

def analyze_test_image(image_path: str):
    """Analyze a test image and show margin filtering details."""
    print(f"\n{'='*60}")
    print(f"Analyzing: {image_path}")
    print(f"{'='*60}")
    
    # Read image
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    # Get OCR service
    ocr_service = OCRService()
    
    try:
        # Call Azure OCR
        from azure.cognitiveservices.vision.computervision import ComputerVisionClient
        from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
        from msrest.authentication import CognitiveServicesCredentials
        from app.config import get_settings
        
        settings = get_settings()
        client = ComputerVisionClient(
            endpoint=settings.AZURE_OCR_ENDPOINT,
            credentials=CognitiveServicesCredentials(settings.AZURE_OCR_KEY)
        )
        
        read_response = client.read_in_stream(
            io.BytesIO(image_bytes),
            raw=True
        )
        
        operation_location = read_response.headers["Operation-Location"]
        operation_id = operation_location.split("/")[-1]
        
        # Wait for operation
        import time
        while True:
            read_result = client.get_read_result(operation_id)
            if read_result.status not in ['notStarted', 'running']:
                break
            time.sleep(1)
        
        if read_result.status == OperationStatusCodes.succeeded:
            # Extract lines with boxes
            lines_with_boxes = []
            for text_result in read_result.analyze_result.read_results:
                for line in text_result.lines:
                    lines_with_boxes.append({
                        'text': line.text,
                        'bounding_box': line.bounding_box
                    })
            
            print(f"\nTotal lines detected: {len(lines_with_boxes)}")
            print(f"\nRaw Azure output:")
            print("-" * 60)
            for i, item in enumerate(lines_with_boxes):
                box = item['bounding_box']
                center_x = (box[0] + box[2] + box[4] + box[6]) / 4
                center_y = (box[1] + box[3] + box[5] + box[7]) / 4
                print(f"{i:2d}: '{item['text'][:50]:<50}' center=({center_x:6.1f}, {center_y:6.1f})")
            
            # Analyze clustering
            print(f"\n{'='*60}")
            print("CLUSTERING ANALYSIS")
            print(f"{'='*60}")
            
            boxes_data = [extract_box_data(item) for item in lines_with_boxes]
            
            # Calculate statistics
            all_x = [b['center_x'] for b in boxes_data]
            all_y = [b['center_y'] for b in boxes_data]
            x_range = max(all_x) - min(all_x)
            y_range = max(all_y) - min(all_y)
            diagonal = (x_range**2 + y_range**2)**0.5
            
            print(f"\nSpatial Statistics:")
            print(f"  X range: {x_range:.1f} px ({min(all_x):.1f} - {max(all_x):.1f})")
            print(f"  Y range: {y_range:.1f} px ({min(all_y):.1f} - {max(all_y):.1f})")
            print(f"  Diagonal: {diagonal:.1f} px")
            print(f"  Epsilon (25%): {diagonal * 0.25:.1f} px")
            
            # Cluster analysis
            clusters = cluster_text_boxes(boxes_data)
            main_cluster, noise = identify_main_content_cluster(clusters, boxes_data)
            
            print(f"\nClustering Results:")
            print(f"  Number of clusters: {len(clusters)}")
            print(f"  Main cluster size: {len(main_cluster)}")
            print(f"  Noise points: {len(noise)}")
            
            for i, cluster in enumerate(clusters):
                print(f"\n  Cluster {i+1} ({len(cluster)} items):")
                for idx in cluster[:5]:  # Show first 5
                    text = boxes_data[idx]['text'][:40]
                    print(f"    - '{text}'")
                if len(cluster) > 5:
                    print(f"    ... and {len(cluster)-5} more")
            
            # Edge detection analysis
            print(f"\n{'='*60}")
            print("EDGE DETECTION ANALYSIS")
            print(f"{'='*60}")
            
            edge_threshold = MARGIN_FILTER_CONFIG['EDGE_PERCENT']
            print(f"\nEdge threshold: {edge_threshold:.1%}")
            print(f"\nItems at extreme edges:")
            
            for i, box_data in enumerate(boxes_data):
                is_edge = is_at_extreme_edge(box_data, boxes_data)
                text = box_data['text']
                
                if is_edge or len(text) <= 3:
                    all_x = [b['center_x'] for b in boxes_data]
                    all_y = [b['center_y'] for b in boxes_data]
                    x_range = max(all_x) - min(all_x)
                    y_range = max(all_y) - min(all_y)
                    
                    from_left = (box_data['center_x'] - min(all_x)) / (x_range + 0.001)
                    from_right = (max(all_x) - box_data['center_x']) / (x_range + 0.001)
                    from_top = (box_data['center_y'] - min(all_y)) / (y_range + 0.001) if y_range > 0 else 0.5
                    from_bottom = (max(all_y) - box_data['center_y']) / (y_range + 0.001) if y_range > 0 else 0.5
                    
                    print(f"\n  Line {i}: '{text[:40]}'")
                    print(f"    Length: {len(text)} chars")
                    print(f"    Position: ({box_data['center_x']:.1f}, {box_data['center_y']:.1f})")
                    print(f"    From edges: L={from_left:.1%}, R={from_right:.1%}, T={from_top:.1%}, B={from_bottom:.1%}")
                    print(f"    Is edge: {is_edge}")
                    print(f"    In main cluster: {i in main_cluster}")
            
            # Filter decision
            print(f"\n{'='*60}")
            print("FILTER DECISIONS")
            print(f"{'='*60}")
            
            filtered = filter_margin_text_c2(lines_with_boxes)
            
            print(f"\nOriginal lines: {len(lines_with_boxes)}")
            print(f"Filtered lines: {len(filtered)}")
            print(f"\nKept lines:")
            for i, text in enumerate(filtered):
                print(f"  {i+1}. '{text[:60]}'")
            
            print(f"\nFiltered out lines:")
            original_texts = [item['text'] for item in lines_with_boxes]
            filtered_set = set(filtered)
            for text in original_texts:
                if text not in filtered_set:
                    print(f"  - '{text[:60]}'")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main function."""
    fixtures_dir = Path('/Users/fernando/ws/photototext/backend/tests/fixtures')
    
    # Analyze each test image
    for image_file in sorted(fixtures_dir.glob('*.jpeg')):
        analyze_test_image(str(image_file))
    
    print(f"\n{'='*60}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
