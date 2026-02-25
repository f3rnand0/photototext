'use client';

import { useState, useCallback } from 'react';
import UploadArea from '@/components/UploadArea';
import TextDisplay from '@/components/TextDisplay';
import { extractTextFromImages } from '@/lib/api';

interface OCRResult {
  filename: string;
  text: string;
  order: number;
}

export default function Home() {
  const [results, setResults] = useState<OCRResult[]>([]);
  const [combinedText, setCombinedText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleFilesSelected = useCallback(async (files: File[]) => {
    if (files.length === 0) return;

    setIsLoading(true);
    setError('');
    setResults([]);
    setCombinedText('');

    try {
      const response = await extractTextFromImages(files);
      
      if (response.success) {
        setResults(response.results);
        setCombinedText(response.combined_text);
      } else {
        setError(response.message || 'Processing failed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  }, []);

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

      {results.length > 0 && (
        <TextDisplay 
          results={results}
          combinedText={combinedText}
        />
      )}
    </main>
  );
}