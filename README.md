# PhotoToText

A web application that extracts text from photos using Azure Computer Vision OCR.

## Features

- **Multi-image upload**: Upload multiple photos at once
- **Order preservation**: Maintains the upload order of images
- **Smart line break cleaning**: Removes line breaks caused by narrow page width while preserving meaningful paragraph breaks
- **Azure OCR**: Uses Azure Computer Vision API for accurate handwriting recognition
- **Copy & Download**: Copy extracted text to clipboard or download as text file

See [ARCHITECTURE.md](ARCHITECTURE.md) for technical details on the system design, data flow, and algorithms.

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- Azure Computer Vision API credentials

### Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your Azure credentials

# Run server (in background)
uvicorn app.main:app --reload > server.log 2>&1 &
```

Backend runs at `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install

# Create .env.local file
cp .env.example .env.local
# Edit .env.local if needed

# Run development server (in the background)
nohup npm run dev  > frontend.log 2>&1 &
```

Frontend runs at `http://localhost:3000`

## Deployment to Render

### 1. Deploy Backend

**Option A: Using Render Dashboard**

1. Go to [render.com](https://render.com) and create an account
2. Click "New +" → "Web Service"
3. Connect your GitHub repo or use "Public Git repository"
4. Configure:
   - **Name**: `photototext-api`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Root Directory**: `backend`
5. Add Environment Variables:
   - `AZURE_OCR_ENDPOINT`: Your Azure endpoint URL
   - `AZURE_OCR_KEY`: Your Azure API key
   - `ALLOWED_ORIGINS`: `*` (or your frontend URL after deployment)
6. Click "Create Web Service"

**Option B: Using render.yaml (Blueprint)**

1. Push code to GitHub
2. In Render dashboard: "New +" → "Blueprint"
3. Connect your repo
4. Render will auto-detect `render.yaml`

### 2. Deploy Frontend

1. In Render dashboard: "New +" → "Static Site"
2. Connect your GitHub repo
3. Configure:
   - **Name**: `photototext`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`
4. Add Environment Variable:
   - `NEXT_PUBLIC_API_URL`: Your backend URL (e.g., `https://photototext-api.onrender.com`)
5. Click "Create Static Site"

### 3. Update CORS

After both are deployed, update backend environment variable:
- `ALLOWED_ORIGINS`: Your frontend URL (e.g., `https://photototext.onrender.com`)

## Updating on Render

Render auto-deploys when you push changes to the connected Git branch.

### Automatic Deployment

1. Commit and push your changes to GitHub:
   ```bash
   git add .
   git commit -m "Your update message"
   git push origin main
   ```

2. Render detects the push and starts a new deploy automatically.

3. Check deployment status:
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click on your service (`photototext-api` or `photototext`)
   - Watch the **Events** tab for build progress
   - Wait for status to change to **Live**

### Manual Deploy (if auto-deploy fails)

1. In Render Dashboard, select your service
2. Click **Manual Deploy** → **Deploy latest commit**
3. Monitor the build logs for errors

### Rolling Back

If a deploy breaks production:
1. In Render Dashboard, go to your service
2. Click **Manual Deploy** → **Deploy a specific commit**
3. Select the last known good commit hash

## Environment Variables

### Backend (.env)

```env
AZURE_OCR_ENDPOINT=https://<your-resource>.cognitiveservices.azure.com/
AZURE_OCR_KEY=<your-key>
ALLOWED_ORIGINS=http://localhost:3000,https://localhost:3000
```

### Frontend (.env.local)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## E2E Testing

The project includes comprehensive E2E tests using pytest.

### Test Structure

```
backend/tests/
├── conftest.py           # Test fixtures and configuration
├── test_e2e.py          # E2E tests
└── fixtures/            # Test images
    ├── 85273A5B-3F64-4DFA-B4B8-8BE6E23D9DD5_4_5005_c.jpeg
    ├── 85DAE903-61D7-435B-8CC6-9CC82B1AD87A_4_5005_c.jpeg
    └── A579D686-84FE-4D76-9EEC-9C02F6446211_4_5005_c.jpeg
```

### Running Tests

**Run all tests:**
```bash
cd backend
pytest tests/ -v
```

**Run specific test:**
```bash
pytest tests/test_e2e.py::TestOCRExtraction::test_extract_text_single_image -v
```

**Run integration test with real Azure OCR:**
```bash
# First, run to see extracted text:
python run_integration_test.py

# Or directly with pytest:
pytest tests/test_e2e.py::test_integration_with_azure -v -s
```

### Updating Expected Results

The E2E tests include a placeholder for expected extracted text. To make the tests reliable:

1. **Run the integration test to see actual extracted text:**
   ```bash
   python run_integration_test.py
   ```

2. **Copy the extracted text from the output**

3. **Update `tests/test_e2e.py`:**
   ```python
   EXPECTED_RESULTS = {
       "85273A5B-3F64-4DFA-B4B8-8BE6E23D9DD5_4_5005_c.jpeg": {
           "expected_text": "The actual extracted text from the image...",
           "description": "First test image"
       },
       # ... update others
   }
   ```

4. **Uncomment the assertions in `test_integration_with_azure`**

### Test Coverage

The E2E tests cover:
- ✅ Single image text extraction
- ✅ Multiple images with order preservation
- ✅ Line break cleaning logic
- ✅ Error handling (no files, invalid type, too many files, too large)
- ✅ Health check endpoint
- ✅ API info endpoint

## File Limits

- Maximum file size: 10MB per image
- Maximum files per request: 20
- Supported formats: PNG, JPG, JPEG, GIF, BMP, TIFF, WEBP

## Azure Free Tier Limits

Azure Computer Vision F0 (Free) tier:
- 5,000 transactions per month
- 1 transaction = 1 image processed

Monitor usage in Azure Portal to avoid overage charges.

## Troubleshooting

### CORS Errors
- Ensure `ALLOWED_ORIGINS` includes your frontend URL
- Use comma-separated list for multiple origins

### OCR Not Working
- Verify Azure credentials are correct
- Check Azure subscription status
- Ensure you're not exceeding free tier limits

### Large Files
- Compress images before upload
- Use lower resolution photos (OCR works fine on 1024px width)

## License

MIT