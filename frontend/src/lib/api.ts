import { logger } from './logger';

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

// Generate unique request ID
function generateRequestId(): string {
  return Math.random().toString(36).substring(2, 10);
}

export async function extractTextFromImages(files: File[]): Promise<ExtractTextResponse> {
  const requestId = generateRequestId();
  const startTime = performance.now();
  
  logger.info('Starting text extraction', {
    requestId,
    fileCount: files.length,
    files: files.map(f => ({ name: f.name, size: f.size, type: f.type })),
    totalSize: files.reduce((sum, f) => sum + f.size, 0),
  });

  const formData = new FormData();
  
  files.forEach((file) => {
    formData.append('files', file);
  });

  try {
    logger.debug('Sending API request', { requestId, endpoint: '/extract-text' });
    
    const response = await fetch(`${API_URL}/extract-text`, {
      method: 'POST',
      body: formData,
      headers: {
        'X-Request-ID': requestId,
      },
    });

    const duration = performance.now() - startTime;
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMessage = errorData.detail || `HTTP ${response.status}: ${response.statusText}`;
      
      logger.error('API request failed', new Error(errorMessage), {
        requestId,
        status: response.status,
        statusText: response.statusText,
        duration: `${duration.toFixed(2)}ms`,
        errorData,
      });
      
      throw new Error(errorMessage);
    }

    const data: ExtractTextResponse = await response.json();
    
    logger.info('Text extraction completed', {
      requestId,
      duration: `${duration.toFixed(2)}ms`,
      success: data.success,
      resultCount: data.results?.length || 0,
      combinedTextLength: data.combined_text?.length || 0,
      message: data.message,
    });
    
    // Log each result
    if (data.results && data.results.length > 0) {
      data.results.forEach((result, index) => {
        logger.debug(`Result ${index + 1}/${data.results.length}`, {
          requestId,
          filename: result.filename,
          textLength: result.text?.length || 0,
          hasError: result.text?.startsWith('Error:') || false,
        });
      });
    }

    return data;
    
  } catch (error) {
    const duration = performance.now() - startTime;
    
    logger.error('Text extraction failed', error instanceof Error ? error : new Error(String(error)), {
      requestId,
      duration: `${duration.toFixed(2)}ms`,
      fileCount: files.length,
    });
    
    throw error;
  }
}

export async function checkHealth(): Promise<{ status: string }> {
  const startTime = performance.now();
  
  logger.debug('Checking API health');
  
  try {
    const response = await fetch(`${API_URL}/health`);
    const data = await response.json();
    
    const duration = performance.now() - startTime;
    logger.debug('Health check completed', { 
      status: data.status, 
      duration: `${duration.toFixed(2)}ms` 
    });
    
    return data;
  } catch (error) {
    logger.error('Health check failed', error instanceof Error ? error : new Error(String(error)));
    throw error;
  }
}

// Progress tracking for sequential processing
export interface ProgressUpdate {
  current: number;
  total: number;
  filename: string;
  status: 'processing' | 'completed' | 'error';
  result?: OCRResult;
  error?: string;
}

export type ProgressCallback = (update: ProgressUpdate) => void;

export async function extractTextFromImagesSequential(
  files: File[],
  onProgress: ProgressCallback,
  signal?: AbortSignal
): Promise<ExtractTextResponse> {
  const startTime = performance.now();
  const results: OCRResult[] = [];
  const errors: string[] = [];
  
  logger.info('Starting sequential text extraction', {
    fileCount: files.length,
    files: files.map(f => ({ name: f.name, size: f.size }))
  });
  
  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    
    // Check if cancelled
    if (signal?.aborted) {
      logger.info('Processing cancelled by user');
      throw new Error('Processing cancelled by user');
    }
    
    // Notify: starting this file
    onProgress({
      current: i + 1,
      total: files.length,
      filename: file.name,
      status: 'processing'
    });
    
    logger.info(`Processing image ${i + 1}/${files.length}: ${file.name}`);
    
    try {
      // Process single file
      const formData = new FormData();
      formData.append('files', file);
      
      const requestId = generateRequestId();
      const response = await fetch(`${API_URL}/extract-text`, {
        method: 'POST',
        body: formData,
        headers: {
          'X-Request-ID': requestId,
        },
        signal
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }
      
      const data: ExtractTextResponse = await response.json();
      
      if (data.success && data.results?.[0]) {
        results.push(data.results[0]);
        
        // Notify: completed
        onProgress({
          current: i + 1,
          total: files.length,
          filename: file.name,
          status: 'completed',
          result: data.results[0]
        });
        
        logger.info(`Completed image ${i + 1}/${files.length}: ${file.name}`, {
          textLength: data.results[0].text.length
        });
      } else {
        throw new Error(data.message || 'Processing failed');
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      errors.push(`${file.name}: ${errorMsg}`);
      
      // Notify: error
      onProgress({
        current: i + 1,
        total: files.length,
        filename: file.name,
        status: 'error',
        error: errorMsg
      });
      
      logger.error(`Failed to process ${file.name}`, error instanceof Error ? error : new Error(errorMsg));
    }
    
    // Brief pause before next image (except after last)
    if (i < files.length - 1) {
      logger.info(`Pausing briefly before next image...`);
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  }
  
  const duration = performance.now() - startTime;
  const combinedText = results.map(r => r.text).join('\n\n');
  
  logger.info('Sequential processing completed', {
    duration: `${duration.toFixed(2)}ms`,
    successCount: results.length,
    errorCount: errors.length,
    totalChars: combinedText.length
  });
  
  return {
    results,
    combined_text: combinedText,
    success: errors.length === 0,
    message: errors.length > 0 
      ? `Processed ${results.length} of ${files.length} images. Errors: ${errors.join(', ')}`
      : `Successfully processed ${results.length} image(s)`
  };
}