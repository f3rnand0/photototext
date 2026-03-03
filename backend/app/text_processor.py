import re
from typing import List, Dict, Any, Tuple, Optional
from app.logger import get_logger

# Get logger
logger = get_logger("text_processor")

# Margin filtering configuration
MARGIN_FILTER_CONFIG = {
    'EPSILON_PERCENT': 0.25,       # 25% of diagonal for clustering (increased from 15%)
    'MIN_SAMPLES': 2,               # Minimum boxes to form cluster
    'EDGE_PERCENT': 0.08,           # 8% from edge considered extreme
    'SHORT_TEXT_MAX': 3,            # Max chars for short text
    'NOISE_EDGE_PERCENT': 0.05,     # 5% for noise filtering
    'DEBUG_MODE': True              # Enable logging
}


def log_filter_decision(text: str, reason: str, details: Optional[Dict[str, Any]] = None):
    """Log filtering decisions for debugging."""
    if MARGIN_FILTER_CONFIG['DEBUG_MODE']:
        context = {"text": text, "reason": reason, **(details or {})}
        logger.debug(f"Margin Filter decision: {reason}", extra={"context": context})


def extract_box_data(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract center coordinates and metadata from bounding box.
    
    Bounding box format: [x1,y1,x2,y2,x3,y3,x4,y4] (corners)
    """
    box = item['bounding_box']
    # Calculate center from all 4 corners
    center_x = (box[0] + box[2] + box[4] + box[6]) / 4
    center_y = (box[1] + box[3] + box[5] + box[7]) / 4
    
    # Calculate bounding box extents
    min_x = min(box[0], box[2], box[4], box[6])
    max_x = max(box[0], box[2], box[4], box[6])
    min_y = min(box[1], box[3], box[5], box[7])
    max_y = max(box[1], box[3], box[5], box[7])
    
    return {
        'text': item['text'],
        'center_x': center_x,
        'center_y': center_y,
        'min_x': min_x,
        'max_x': max_x,
        'min_y': min_y,
        'max_y': max_y,
        'width': max_x - min_x,
        'height': max_y - min_y,
        'box': box,
        'original': item
    }


def calculate_distance(box1: Dict[str, Any], box2: Dict[str, Any]) -> float:
    """Calculate Euclidean distance between two box centers."""
    return ((box1['center_x'] - box2['center_x'])**2 + 
            (box1['center_y'] - box2['center_y'])**2) ** 0.5


def cluster_text_boxes(boxes_data: List[Dict[str, Any]], 
                       epsilon_percent: Optional[float] = None,
                       min_samples: Optional[int] = None) -> List[List[int]]:
    """
    Cluster text boxes using DBSCAN-style distance-based clustering.
    
    Args:
        boxes_data: List of box data dictionaries
        epsilon_percent: Max distance as percentage of bounding box diagonal
        min_samples: Minimum boxes to form a cluster
        
    Returns:
        List of clusters, where each cluster is a list of indices
    """
    # Get config values with defaults
    eps_percent = epsilon_percent if epsilon_percent is not None else MARGIN_FILTER_CONFIG['EPSILON_PERCENT']
    min_samp = min_samples if min_samples is not None else MARGIN_FILTER_CONFIG['MIN_SAMPLES']
    
    n = len(boxes_data)
    if n < min_samp:
        logger.info(f"Margin Filter: Too few boxes ({n}), treating as single cluster")
        return [list(range(n))]
    
    # Calculate epsilon in pixels based on bounding box diagonal
    all_x = [b['center_x'] for b in boxes_data]
    all_y = [b['center_y'] for b in boxes_data]
    
    x_range = max(all_x) - min(all_x)
    y_range = max(all_y) - min(all_y)
    diagonal = (x_range**2 + y_range**2) ** 0.5
    epsilon = diagonal * eps_percent
    
    logger.info(f"Margin Filter: Clustering with epsilon={epsilon:.1f}px "
                f"({eps_percent*100:.0f}% of {diagonal:.1f}px diagonal)")
    
    # DBSCAN implementation
    visited = [False] * n
    clusters = []
    noise = []
    
    for i in range(n):
        if visited[i]:
            continue
        
        # Find neighbors within epsilon
        neighbors = []
        for j in range(n):
            if i != j:
                dist = calculate_distance(boxes_data[i], boxes_data[j])
                if dist <= epsilon:
                    neighbors.append(j)
        
        if len(neighbors) < min_samp:
            # Mark as potential noise (isolated)
            # Don't add to noise list yet - might be border point later
            visited[i] = True
            continue
        
        # Start new cluster
        cluster = [i]
        visited[i] = True
        
        # Expand cluster
        queue = neighbors[:]
        idx = 0
        while idx < len(queue):
            neighbor = queue[idx]
            idx += 1
            
            # Add neighbor to cluster if not already in it
            # (even if previously marked as noise - it's a border point)
            if neighbor not in cluster:
                cluster.append(neighbor)
                
                # Only expand if this neighbor hasn't been processed before
                if not visited[neighbor]:
                    visited[neighbor] = True
                    
                    # Find neighbors of this neighbor
                    new_neighbors = []
                    for k in range(n):
                        if k != neighbor and not visited[k]:
                            dist = calculate_distance(boxes_data[neighbor], boxes_data[k])
                            if dist <= epsilon:
                                new_neighbors.append(k)
                    
                    # If this neighbor is a core point, add its neighbors to queue
                    if len(new_neighbors) >= min_samp - 1:  # -1 because we count the point itself too
                        queue.extend(new_neighbors)
        
        clusters.append(cluster)
    
    logger.info(f"Margin Filter: Found {len(clusters)} clusters, {len(noise)} noise points")
    for i, cluster in enumerate(clusters):
        total_chars = sum(len(boxes_data[j]['text'].strip()) for j in cluster)
        logger.info(f"  Cluster {i+1}: {len(cluster)} boxes, {total_chars} chars")
    
    return clusters


def identify_main_content_cluster(clusters: List[List[int]], 
                                  boxes_data: List[Dict[str, Any]]) -> Tuple[List[int], List[int]]:
    """
    Identify the main content cluster (largest by character count).
    
    Returns:
        Tuple of (main_cluster_indices, noise_indices)
    """
    if not clusters:
        return [], list(range(len(boxes_data)))
    
    # Score each cluster by total character count
    cluster_scores = []
    for cluster in clusters:
        total_chars = sum(len(boxes_data[i]['text'].strip()) for i in cluster)
        cluster_scores.append((cluster, total_chars))
    
    # Sort by score descending
    cluster_scores.sort(key=lambda x: x[1], reverse=True)
    
    main_cluster = cluster_scores[0][0]
    
    # All indices not in main cluster are considered noise
    all_clustered = set()
    for cluster in clusters:
        all_clustered.update(cluster)
    
    noise_indices = [i for i in range(len(boxes_data)) if i not in all_clustered]
    
    logger.info(f"Margin Filter: Main cluster has {len(main_cluster)} boxes, "
                f"{cluster_scores[0][1]} chars")
    
    return main_cluster, noise_indices


def is_at_extreme_edge(box_data: Dict[str, Any], 
                       all_boxes: List[Dict[str, Any]], 
                       edge_percent: Optional[float] = None) -> bool:
    """
    Check if text is at extreme edge using percentage-based thresholds.
    
    Args:
        edge_percent: Percentage from edge to consider extreme
    """
    # Get config value with default
    edge_pct = edge_percent if edge_percent is not None else MARGIN_FILTER_CONFIG['EDGE_PERCENT']
    
    all_x = [b['center_x'] for b in all_boxes]
    all_y = [b['center_y'] for b in all_boxes]
    
    x_range = max(all_x) - min(all_x)
    y_range = max(all_y) - min(all_y)
    
    # Only return False if we can't calculate any ranges
    if x_range == 0 and y_range == 0:
        return False
    
    center_x = box_data['center_x']
    center_y = box_data['center_y']
    
    # Calculate position as percentage from each edge
    # Avoid division by zero by using small epsilon
    from_left = (center_x - min(all_x)) / (x_range + 0.001)
    from_right = (max(all_x) - center_x) / (x_range + 0.001)
    from_top = (center_y - min(all_y)) / (y_range + 0.001) if y_range > 0 else 0.5
    from_bottom = (max(all_y) - center_y) / (y_range + 0.001) if y_range > 0 else 0.5
    
    is_edge = (from_left < edge_pct or 
               from_right < edge_pct or
               from_top < edge_pct or 
               from_bottom < edge_pct)
    
    if is_edge and MARGIN_FILTER_CONFIG['DEBUG_MODE']:
        edge_details = {
            'from_left': f"{from_left:.1%}",
            'from_right': f"{from_right:.1%}",
            'from_top': f"{from_top:.1%}",
            'from_bottom': f"{from_bottom:.1%}",
            'threshold': f"{edge_pct:.1%}"
        }
        logger.debug(f"  Edge detection: at extreme edge - {edge_details}")
    
    return is_edge


def filter_margin_text_c2(lines_with_boxes: List[Dict[str, Any]]) -> List[str]:
    """
    Filter margin text using distance-based clustering (DBSCAN-style).
    
    Filters:
    - Short text (<=3 chars) at extreme edges
    - Isolated text not in main cluster
    - Page numbers, headers, footers
    
    Keeps:
    - Text in main content cluster
    - Isolated text not at extreme edges (might be legitimate)
    """
    if not lines_with_boxes:
        logger.info("Margin Filter: No input data")
        return []
    
    if len(lines_with_boxes) < 3:
        logger.info(f"Margin Filter: Too few lines ({len(lines_with_boxes)}), skipping filtering")
        return [item['text'] for item in lines_with_boxes]
    
    logger.info(f"Margin Filter: Processing {len(lines_with_boxes)} text lines", extra={
        "context": {"input_line_count": len(lines_with_boxes)}
    })
    
    # Extract box data
    boxes_data = [extract_box_data(item) for item in lines_with_boxes]
    
    # Cluster text
    clusters = cluster_text_boxes(boxes_data)
    main_cluster, noise_indices = identify_main_content_cluster(clusters, boxes_data)
    
    # Identify edge clusters (small clusters at extreme edges)
    def is_edge_cluster(cluster_indices, all_boxes_data):
        """Check if a cluster is primarily at the edge."""
        if len(cluster_indices) == 0:
            return False
        
        # Check what percentage of cluster items are at extreme edges
        edge_count = sum(1 for idx in cluster_indices 
                        if is_at_extreme_edge(all_boxes_data[idx], all_boxes_data))
        
        return edge_count >= len(cluster_indices) * 0.75  # 75% at edge
    
    # Find edge clusters (non-main clusters that are at edges)
    edge_clusters = set()
    for cluster in clusters:
        if cluster == main_cluster:
            continue
        
        # Small cluster at edge = likely margin text
        cluster_size_ratio = len(cluster) / len(main_cluster) if main_cluster else 1
        if cluster_size_ratio < 0.3 and is_edge_cluster(cluster, boxes_data):  # Less than 30% of main
            edge_clusters.update(cluster)
            logger.info(f"Margin Filter: Identified edge cluster with {len(cluster)} items")
    
    # Filter logic
    filtered = []
    filtered_count = 0
    
    config = MARGIN_FILTER_CONFIG
    
    for i, box_data in enumerate(boxes_data):
        text = box_data['text'].strip()
        text_len = len(text)
        
        # Case 1: Short text at extreme edges - filter (check this FIRST)
        # This catches margin text even if it's accidentally clustered with main content
        if text_len <= config['SHORT_TEXT_MAX']:
            if is_at_extreme_edge(box_data, boxes_data, config['EDGE_PERCENT']):
                log_filter_decision(text, "FILTERED", {
                    'reason': 'short_text_at_edge',
                    'length': text_len,
                    'max_short_length': config['SHORT_TEXT_MAX']
                })
                filtered_count += 1
                continue
        
        # Case 2: In main cluster - keep
        if i in main_cluster:
            log_filter_decision(text, "KEPT", {
                'reason': 'in_main_cluster',
                'cluster_size': len(main_cluster)
            })
            filtered.append(text)
            continue
        
        # Case 3: In edge cluster - filter
        if i in edge_clusters:
            log_filter_decision(text, "FILTERED", {
                'reason': 'in_edge_cluster',
                'cluster_type': 'margin_text'
            })
            filtered_count += 1
            continue
        
        # Case 4: Noise at extreme edges - filter
        if i in noise_indices:
            if is_at_extreme_edge(box_data, boxes_data, config['NOISE_EDGE_PERCENT']):
                log_filter_decision(text, "FILTERED", {
                    'reason': 'noise_at_edge',
                    'edge_threshold': f"{config['NOISE_EDGE_PERCENT']:.1%}"
                })
                filtered_count += 1
                continue
            else:
                # Noise but not at edge - might be legitimate isolated text
                log_filter_decision(text, "KEPT", {
                    'reason': 'noise_not_at_edge',
                    'note': 'isolated but not at extreme edge'
                })
        
        # Keep everything else
        filtered.append(text)
    
    logger.info(f"Margin Filter: Complete", extra={"context": {
        "input_lines": len(lines_with_boxes),
        "kept_lines": len(filtered),
        "filtered_lines": filtered_count,
        "kept_percentage": f"{(len(filtered)/len(lines_with_boxes)*100):.1f}%"
    }})
    
    return filtered


def filter_margin_text(lines_with_boxes: List[Dict[str, Any]]) -> List[str]:
    """
    Backward-compatible wrapper that uses the new C2 algorithm.
    """
    return filter_margin_text_c2(lines_with_boxes)


def split_title_lines(text: str) -> str:
    """
    Split lines that contain titles/headers followed by content.
    
    Detects patterns like:
    - "* Title * Rest of sentence" -> "* Title *\nRest of sentence"
    - "Title: Content" where Title is short
    
    This handles cases where Azure OCR joins titles with following text.
    """
    lines = text.split('\n')
    result_lines = []
    
    for line in lines:
        line = line.rstrip()
        if not line:
            result_lines.append(line)
            continue
        
        # Pattern 1: Text surrounded by * (like * Title *)
        # Split after the closing *
        title_match = re.search(r'^(\*[^*]+\*)\s+(.+)$', line)
        if title_match:
            title_part = title_match.group(1).strip()
            rest_part = title_match.group(2).strip()
            if title_part and rest_part:
                result_lines.append(title_part)
                result_lines.append(rest_part)
                continue
        
        result_lines.append(line)
    
    return '\n'.join(result_lines)


def remove_spaces_before_punctuation(text: str) -> str:
    """
    Remove spaces before punctuation marks.
    
    Handles punctuation in German, English, and Spanish:
    . , ! ? : ; ) ] } » " ' 
    
    Args:
        text: Input text
        
    Returns:
        Text with spaces before punctuation removed
    """
    # List of punctuation marks that should not have space before
    punctuation_marks = r'.,!?:;\)\]\}»"\''
    
    # Pattern: one or more spaces followed by punctuation
    # Replace with just the punctuation
    pattern = rf'\s+([{re.escape(punctuation_marks)}])'
    text = re.sub(pattern, r'\1', text)
    
    return text


def join_hyphenated_words(text: str) -> str:
    """
    Join syllables separated by hyphens.
    
    Handles:
    - "word-\nword" (newline continuation)
    - "word- word" (space continuation)
    
    Args:
        text: Input text
        
    Returns:
        Text with hyphenated syllables joined
    """
    # Pattern 1: hyphen followed by newline and then word
    # word-\nword → wordword
    text = re.sub(r'(\w+)-\n+(\w+)', r'\1\2', text)
    
    # Pattern 2: hyphen followed by space and then word
    # word- word → wordword
    text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', text)
    
    return text


def clean_line_breaks(text: str) -> str:
    """
    Remove line breaks caused by narrow page width.
    Keep meaningful paragraph breaks.
    
    Rules:
    - Join lines if previous line doesn't end with sentence-ending punctuation
    - Join lines if next line starts with lowercase letter
    - Keep breaks if line is significantly shorter than average (titles/headers)
    - Keep breaks if line ends with : (list intros, quotes)
    """
    if not text or not text.strip():
        return text
    
    # First, split any lines that contain embedded titles
    text = split_title_lines(text)
    
    lines = text.split('\n')
    
    # Calculate statistics for short line detection
    non_empty_lengths = []
    
    for line in lines:
        stripped = line.strip()
        length = len(stripped) if stripped else 0
        if stripped:
            non_empty_lengths.append(length)
    
    avg_all = sum(non_empty_lengths) / len(non_empty_lengths) if non_empty_lengths else 0
    max_length = max(non_empty_lengths) if non_empty_lengths else 0
    
    cleaned_lines = []
    current_paragraph = []
    
    # Sentence ending punctuation (including : for lists/introductory phrases)
    sentence_enders = '.!?:'
    
    for i, line in enumerate(lines):
        line = line.rstrip()
        if not line:
            # Empty line = intentional paragraph break
            if current_paragraph:
                cleaned_lines.append(' '.join(current_paragraph))
                current_paragraph = []
            continue
        
        # Check if line is "short" (likely a title/heading/standalone line)
        line_len = len(line)
        
        # A line is "short" if it meets ANY of these criteria:
        is_short_line = False
        
        # Calculate average of other non-empty lines
        other_lengths = [l for j, l in enumerate(non_empty_lengths) if j != i]
        avg_others = sum(other_lengths) / len(other_lengths) if other_lengths else avg_all
        
        # Criteria 1: Has explicit title markers (*text*, **text**, etc.)
        has_title_markers = bool(re.search(r'\*+[^*]+\*+', line))
        
        # Criteria 2: Is very short (< 30 chars) compared to others
        is_very_short = line_len < 30 and avg_others > 50
        
        # Criteria 3: Significantly shorter than average (< 50% of others)
        is_much_shorter = line_len < avg_others * 0.5 and line_len < 40
        
        if has_title_markers or is_very_short or is_much_shorter:
            is_short_line = True
        
        # Check if line ends with sentence terminator
        ends_with_punct = line[-1] in sentence_enders if line else False
        
        # Check if next line exists and starts with lowercase
        next_starts_lower = False
        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if next_line and next_line[0].islower():
                next_starts_lower = True
        
        # Paragraph break triggers:
        # 1. Line ends with punctuation and next doesn't start lowercase
        # 2. Line is significantly shorter than average (title/header)
        if (ends_with_punct and not next_starts_lower) or is_short_line:
            # Likely end of sentence/paragraph or standalone line
            current_paragraph.append(line)
            cleaned_lines.append(' '.join(current_paragraph))
            current_paragraph = []
        else:
            # Likely wrapped line - add to current paragraph
            current_paragraph.append(line)
    
    # Don't forget last paragraph
    if current_paragraph:
        cleaned_lines.append(' '.join(current_paragraph))
    
    # Join paragraphs with double newline
    result = '\n\n'.join(cleaned_lines)
    
    # Clean up multiple spaces
    result = re.sub(r' +', ' ', result)
    
    return result.strip()


def process_extracted_text(lines_with_boxes: List[Dict[str, Any]]) -> str:
    """
    Main processing pipeline for extracted OCR text.
    
    Pipeline:
    1. Filter margin text (remove adjacent page content)
    2. Join text lines
    3. Join hyphenated words
    4. Remove spaces before punctuation
    5. Clean line breaks
    
    Args:
        lines_with_boxes: List of dicts with 'text' and 'bounding_box' keys
        
    Returns:
        Cleaned and processed text
    """
    import time
    start_time = time.time()
    
    logger.info("Text processing pipeline started", extra={"context": {
        "input_lines": len(lines_with_boxes),
        "total_input_chars": sum(len(line.get('text', '')) for line in lines_with_boxes)
    }})
    
    # Step 1: Filter out margin text
    step1_start = time.time()
    filtered_lines = filter_margin_text(lines_with_boxes)
    step1_duration = time.time() - step1_start
    
    if not filtered_lines:
        logger.info("Text processing: No content after margin filtering")
        return ""
    
    logger.debug(f"Step 1 (margin filter) completed in {step1_duration:.3f}s", extra={"context": {
        "step": "margin_filter",
        "duration_seconds": f"{step1_duration:.3f}",
        "lines_after_filter": len(filtered_lines)
    }})
    
    # Step 2: Join lines with newlines for processing
    step2_start = time.time()
    text = '\n'.join(filtered_lines)
    step2_duration = time.time() - step2_start
    
    # Step 3: Join hyphenated words
    step3_start = time.time()
    text = join_hyphenated_words(text)
    step3_duration = time.time() - step3_start
    
    logger.debug(f"Step 3 (hyphenation) completed in {step3_duration:.3f}s", extra={"context": {
        "step": "join_hyphens",
        "duration_seconds": f"{step3_duration:.3f}",
        "text_length": len(text)
    }})
    
    # Step 4: Remove spaces before punctuation
    step4_start = time.time()
    text = remove_spaces_before_punctuation(text)
    step4_duration = time.time() - step4_start
    
    # Step 5: Clean line breaks within the text
    step5_start = time.time()
    text = clean_line_breaks(text)
    step5_duration = time.time() - step5_start
    
    logger.debug(f"Step 5 (line breaks) completed in {step5_duration:.3f}s", extra={"context": {
        "step": "clean_line_breaks",
        "duration_seconds": f"{step5_duration:.3f}",
        "text_length": len(text)
    }})
    
    total_duration = time.time() - start_time
    
    logger.info("Text processing pipeline completed", extra={"context": {
        "input_lines": len(lines_with_boxes),
        "output_lines": len(filtered_lines),
        "output_chars": len(text),
        "total_duration_seconds": f"{total_duration:.3f}",
        "compression_ratio": f"{(len(text) / max(sum(len(line.get('text', '')) for line in lines_with_boxes), 1) * 100):.1f}%"
    }})
    
    return text
