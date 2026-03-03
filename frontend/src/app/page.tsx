'use client';

import { useState, useCallback } from 'react';
import UploadArea from '@/components/UploadArea';
import TextDisplay from '@/components/TextDisplay';
import { extractTextFromImagesSequential, ProgressUpdate } from '@/lib/api';
import { logger } from '@/lib/logger';

interface OCRResult {
  filename: string;
  text: string;
  order: number;
}

interface ProcessingState {
  isActive: boolean;
  current: number;
  total: number;
  currentFile: string;
  abortController: AbortController;
}

export default function Home() {
  const [results, setResults] = useState<OCRResult[]>([]);
  const [combinedText, setCombinedText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [processingState, setProcessingState] = useState<ProcessingState | null>(null);

  logger.info('Home component mounted');

  const handleFilesSelected = useCallback(async (files: File[]) => {
    if (files.length === 0) {
      logger.warn('handleFilesSelected called with empty files array');
      return;
    }

    logger.info('Processing started', { fileCount: files.length });
    
    // Create abort controller for cancellation
    const abortController = new AbortController();
    
    setProcessingState({
      isActive: true,
      current: 0,
      total: files.length,
      currentFile: 'Starting...',
      abortController
    });
    
    setIsLoading(true);
    setError('');
    setResults([]);
    setCombinedText('');

    try {
      const response = await extractTextFromImagesSequential(
        files,
        (progress: ProgressUpdate) => {
          setProcessingState(prev => prev ? {
            ...prev,
            current: progress.current,
            currentFile: progress.filename
          } : null);
        },
        abortController.signal
      );
      
      if (response.success) {
        logger.info('Processing successful', { 
          resultCount: response.results.length,
          combinedTextLength: response.combined_text.length 
        });
        setResults(response.results);
        setCombinedText(response.combined_text);
      } else {
        logger.warn('Processing returned unsuccessful response', { message: response.message });
        setError(response.message || 'Processing completed with errors');
      }
    } catch (err) {
      if (err instanceof Error && err.message === 'Processing cancelled by user') {
        logger.info('Processing cancelled by user');
        setError('Processing cancelled by user');
      } else {
        const errorMessage = err instanceof Error ? err.message : 'An error occurred';
        logger.error('Processing failed', err instanceof Error ? err : new Error(errorMessage));
        setError(errorMessage);
      }
    } finally {
      setProcessingState(null);
      setIsLoading(false);
    }
  }, []);

  const handleCancel = useCallback(() => {
    if (processingState?.abortController) {
      logger.info('User clicked cancel button');
      processingState.abortController.abort();
    }
  }, [processingState]);

  const ProgressBar = ({ current, total, currentFile }: { current: number; total: number; currentFile: string }) => {
    const percentage = Math.round((current / total) * 100);
    const estimatedSeconds = total * 10; // Rough estimate: 10 seconds per image
    
    return (
      <div style={{ marginTop: '20px', marginBottom: '20px' }}>
        {/* Warning Message */}
        <div style={{
          padding: '12px 16px',
          backgroundColor: '#fef3c7',
          border: '1px solid #f59e0b',
          borderRadius: '8px',
          marginBottom: '16px',
          color: '#92400e',
          fontSize: '14px'
        }}>
          Processing {total} images. This will take approximately {Math.ceil(estimatedSeconds / 10) * 10}-{Math.ceil(estimatedSeconds / 10) * 10 + total * 5} seconds due to API rate limits.
        </div>
        
        {/* Progress Bar Container */}
        <div style={{ marginBottom: '12px' }}>
          <div style={{
            height: '8px',
            backgroundColor: '#e5e7eb',
            borderRadius: '4px',
            overflow: 'hidden'
          }}>
            <div style={{
              height: '100%',
              width: `${percentage}%`,
              backgroundColor: '#3b82f6',
              borderRadius: '4px',
              transition: 'width 0.5s ease-in-out'
            }} />
          </div>
        </div>
        
        {/* Progress Text */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '14px',
          color: '#374151',
          marginBottom: '16px'
        }}>
          <span>
            Processing: <strong>{currentFile}</strong>
          </span>
          <span>
            {current} of {total} ({percentage}%)
          </span>
        </div>
        
        {/* Cancel Button */}
        <button
          onClick={handleCancel}
          style={{
            padding: '8px 16px',
            backgroundColor: '#ef4444',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: '500'
          }}
        >
          Cancel Processing
        </button>
      </div>
    );
  };

  return (
    <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '20px' }}>
      <h1 style={{ 
        textAlign: 'center', 
        marginBottom: '10px',
        color: '#333'
      }}>
        PhotoToText
      </h1>
      
      <p style={{ 
        textAlign: 'center', 
        color: '#666',
        marginBottom: '30px'
      }}>
        Upload photos with text. We&apos;ll extract the text and preserve paragraphs.
      </p>

      <UploadArea 
        onFilesSelected={handleFilesSelected}
        isLoading={isLoading}
      />

      {processingState?.isActive && (
        <ProgressBar 
          current={processingState.current}
          total={processingState.total}
          currentFile={processingState.currentFile}
        />
      )}

      {error && (
        <div style={{
          marginTop: '20px',
          padding: '15px',
          backgroundColor: '#fee2e2',
          border: '1px solid #ef4444',
          borderRadius: '8px',
          color: '#dc2626'
        }}>
          {error}
        </div>
      )}

      {results.length > 0 && !processingState?.isActive && (
        <TextDisplay 
          results={results}
          combinedText={combinedText}
        />
      )}
    </main>
  );
}
