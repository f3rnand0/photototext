const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface OCRResult {
  filename: string;
  text: string;
  order: number;
}

interface ExtractTextResponse {
  results: OCRResult[];
  combined_text: string;
  success: boolean;
  message: string;
}

export async function extractTextFromImages(files: File[]): Promise<ExtractTextResponse> {
  const formData = new FormData();
  
  files.forEach((file) => {
    formData.append('files', file);
  });

  const response = await fetch(`${API_URL}/extract-text`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to extract text');
  }

  return response.json();
}

export async function checkHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_URL}/health`);
  return response.json();
}