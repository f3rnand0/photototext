# PhotoToText Architecture

## Overview

PhotoToText is a web application that extracts text from photos using Azure Computer Vision OCR. It consists of a Next.js frontend, a FastAPI backend, and the Azure Computer Vision API.

```
Frontend (Next.js)  ←→  Backend (FastAPI)  ←→  Azure Computer Vision API
      (Render)             (Render)
```

## Project Structure

```
photototext/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── main.py       # FastAPI routes
│   │   ├── ocr_service.py    # Azure OCR integration + image compression
│   │   ├── text_processor.py # Line break cleaning + margin filtering
│   │   ├── config.py     # Configuration
│   │   └── models.py     # Pydantic models
│   ├── tests/            # E2E and unit tests
│   │   ├── test_e2e.py
│   │   ├── test_margin_filter.py
│   │   ├── conftest.py
│   │   └── fixtures/     # Test images
│   ├── requirements.txt
│   ├── render.yaml       # Render deployment config
│   └── .env.example      # Environment variables template
└── frontend/             # Next.js application
    ├── src/
    │   ├── app/          # Next.js pages
    │   ├── components/   # React components
    │   └── lib/          # API client
    ├── package.json
    └── next.config.js
```

## Data Flow

### Single Image OCR

1. **Frontend** uploads image via `POST /extract-text` (sequential mode sends one image per request)
2. **Backend** receives the image, compresses it (max 2000px dimension, JPEG quality 85)
3. **Backend** sends compressed image to Azure Read API
4. **Azure** processes the image asynchronously (typically ~3 minutes for a standard photo)
5. **Backend** polls Azure every 3 seconds for up to 100 polls (~300s max)
6. **Backend** applies text processing:
   - Margin text filtering (remove text from adjacent pages)
   - Line break cleaning (remove wrapping breaks, keep paragraph breaks)
7. **Backend** returns cleaned text to frontend

## OCR Pipeline Configuration

| Constant | Value | Purpose |
|---|---|---|
| `MAX_DIMENSION` | `2000` | Max pixels on longest side before resizing |
| `JPEG_QUALITY` | `85` | JPEG quality for compression |
| `OCR_TIMEOUT` | `100 polls` | Max Azure polling attempts |
| `POLL_INTERVAL` | `3 seconds` | Time between poll requests |

**Why 3-second polling?**  
With 1-second polling, HTTP connection pooling causes ~40-second hangs every ~20 polls. The 3-second interval avoids connection reuse issues and reduces total API calls.

## Line Break Processing Logic

The application intelligently handles line breaks to distinguish text wrapping from real paragraph breaks:

**Keeps breaks when:**
- Line ends with sentence punctuation (`.`, `!`, `?`)
- Next line starts with uppercase letter
- Empty lines (intentional paragraph breaks)

**Joins lines when:**
- Previous line doesn't end with punctuation
- Next line starts with lowercase letter
- Indicates text wrapping due to narrow page

## Margin Text Filtering

Azure OCR sometimes extracts text from adjacent pages that appear in image margins. The backend filters these out using a distance-based clustering approach.

### Algorithm

1. **Spatial Clustering** (DBSCAN-style)
   - Groups text boxes based on proximity (epsilon = 25% of image diagonal)
   - Identifies the main content cluster (largest by character count)
   - Detects smaller clusters at edges

2. **Multi-Stage Filtering Logic:**
   - **Priority 1**: Short text (≤3 chars) at extreme edges → FILTERED
   - **Priority 2**: Text in main cluster → KEPT
   - **Priority 3**: Text in edge clusters (small clusters at edges) → FILTERED
   - **Priority 4**: Noise points at edges → FILTERED

3. **Edge Detection**
   - Uses percentage-based thresholds (8% from any edge)
   - Handles variable image sizes
   - Detects left, right, top, and bottom edges

### Configuration Parameters

```python
MARGIN_FILTER_CONFIG = {
    'EPSILON_PERCENT': 0.25,    # 25% of diagonal for clustering
    'MIN_SAMPLES': 2,            # Minimum boxes to form cluster
    'EDGE_PERCENT': 0.08,        # 8% from edge considered extreme
    'SHORT_TEXT_MAX': 3,         # Max chars for short text
    'NOISE_EDGE_PERCENT': 0.05,  # 5% for noise filtering
    'DEBUG_MODE': True           # Enable detailed logging
}
```

## API Endpoints

### `POST /extract-text`

Extract text from uploaded images.

**Request**: `multipart/form-data`
- `files`: Array of image files (PNG, JPG, etc.)

**Response**:
```json
{
  "results": [
    {
      "filename": "page1.jpg",
      "text": "Extracted text with proper paragraphs...",
      "order": 0
    }
  ],
  "combined_text": "All text combined with \\n\\n between images",
  "success": true,
  "message": "Successfully processed 1 image(s)"
}
```

### `GET /health`

Health check endpoint.

### `GET /`

API info endpoint.

## File Limits

- Maximum file size: 10MB per image
- Maximum files per request: 20
- Supported formats: PNG, JPG, JPEG, GIF, BMP, TIFF, WEBP

## Azure Free Tier Limits

Azure Computer Vision F0 (Free) tier:
- 5,000 transactions per month
- 1 transaction = 1 image processed

Monitor usage in Azure Portal to avoid overage charges.
