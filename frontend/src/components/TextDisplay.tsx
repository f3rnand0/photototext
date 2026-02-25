'use client';

import { useState, useCallback } from 'react';

interface OCRResult {
  filename: string;
  text: string;
  order: number;
}

interface TextDisplayProps {
  results: OCRResult[];
  combinedText: string;
}

export default function TextDisplay({ results, combinedText }: TextDisplayProps) {
  const [activeTab, setActiveTab] = useState<'combined' | 'individual'>('combined');
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, []);

  const handleDownload = useCallback(() => {
    const blob = new Blob([combinedText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'extracted-text.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [combinedText]);

  return (
    <div style={{ marginTop: '30px' }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '15px',
        flexWrap: 'wrap',
        gap: '10px'
      }}>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => setActiveTab('combined')}
            style={{
              padding: '8px 16px',
              backgroundColor: activeTab === 'combined' ? '#3b82f6' : '#f3f4f6',
              color: activeTab === 'combined' ? 'white' : '#374151',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '500'
            }}
          >
            Combined Text
          </button>
          <button
            onClick={() => setActiveTab('individual')}
            style={{
              padding: '8px 16px',
              backgroundColor: activeTab === 'individual' ? '#3b82f6' : '#f3f4f6',
              color: activeTab === 'individual' ? 'white' : '#374151',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '500'
            }}
          >
            Individual Results ({results.length})
          </button>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => handleCopy(combinedText)}
            style={{
              padding: '8px 16px',
              backgroundColor: copied ? '#10b981' : '#f3f4f6',
              color: copied ? 'white' : '#374151',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            {copied ? '✓ Copied!' : '📋 Copy All'}
          </button>
          <button
            onClick={handleDownload}
            style={{
              padding: '8px 16px',
              backgroundColor: '#f3f4f6',
              color: '#374151',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            💾 Download
          </button>
        </div>
      </div>

      {activeTab === 'combined' ? (
        <div style={{
          backgroundColor: '#f9fafb',
          border: '1px solid #e5e7eb',
          borderRadius: '8px',
          padding: '20px',
          minHeight: '300px'
        }}>
          <pre style={{
            margin: 0,
            whiteSpace: 'pre-wrap',
            wordWrap: 'break-word',
            fontFamily: 'system-ui, -apple-system, sans-serif',
            fontSize: '16px',
            lineHeight: '1.6',
            color: '#1f2937'
          }}>
            {combinedText || 'No text extracted'}
          </pre>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
          {results.map((result, index) => (
            <div
              key={result.filename}
              style={{
                backgroundColor: '#f9fafb',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                padding: '15px'
              }}
            >
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '10px',
                paddingBottom: '10px',
                borderBottom: '1px solid #e5e7eb'
              }}>
                <span style={{ fontWeight: '600', color: '#374151' }}>
                  #{index + 1}: {result.filename}
                </span>
                <button
                  onClick={() => handleCopy(result.text)}
                  style={{
                    padding: '4px 12px',
                    backgroundColor: '#f3f4f6',
                    color: '#374151',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '12px'
                  }}
                >
                  Copy
                </button>
              </div>
              <pre style={{
                margin: 0,
                whiteSpace: 'pre-wrap',
                wordWrap: 'break-word',
                fontFamily: 'system-ui, -apple-system, sans-serif',
                fontSize: '14px',
                lineHeight: '1.5',
                color: '#4b5563'
              }}>
                {result.text || 'No text found in this image'}
              </pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}