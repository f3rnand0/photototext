'use client';

import { useCallback, useState } from 'react';

interface UploadAreaProps {
  onFilesSelected: (files: File[]) => void;
  isLoading: boolean;
}

const ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/bmp', 'image/tiff', 'image/webp'];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

export default function UploadArea({ onFilesSelected, isLoading }: UploadAreaProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [validationError, setValidationError] = useState('');

  const validateFile = (file: File): string | null => {
    if (!ALLOWED_TYPES.includes(file.type)) {
      return `${file.name}: Invalid file type. Allowed: PNG, JPG, GIF, BMP, TIFF, WEBP`;
    }
    if (file.size > MAX_FILE_SIZE) {
      return `${file.name}: File too large (max 10MB)`;
    }
    return null;
  };

  const handleFiles = useCallback((files: FileList | null) => {
    if (!files) return;

    setValidationError('');
    const fileArray = Array.from(files);
    
    // Validate all files
    for (const file of fileArray) {
      const error = validateFile(file);
      if (error) {
        setValidationError(error);
        return;
      }
    }

    setSelectedFiles(fileArray);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  }, [handleFiles]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    handleFiles(e.target.files);
  }, [handleFiles]);

  const handleSubmit = useCallback(() => {
    if (selectedFiles.length > 0) {
      onFilesSelected(selectedFiles);
    }
  }, [selectedFiles, onFilesSelected]);

  const clearFiles = useCallback(() => {
    setSelectedFiles([]);
    setValidationError('');
  }, []);

  return (
    <div>
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        style={{
          border: `3px dashed ${isDragging ? '#3b82f6' : '#d1d5db'}`,
          borderRadius: '12px',
          padding: '40px',
          textAlign: 'center',
          backgroundColor: isDragging ? '#eff6ff' : '#f9fafb',
          transition: 'all 0.2s',
          cursor: 'pointer',
        }}
      >
        <input
          type="file"
          accept="image/*"
          multiple
          onChange={handleFileInput}
          style={{ display: 'none' }}
          id="file-input"
        />
        <label htmlFor="file-input" style={{ cursor: 'pointer' }}>
          <div style={{ fontSize: '48px', marginBottom: '10px' }}>📁</div>
          <p style={{ margin: '0 0 10px 0', color: '#374151', fontSize: '16px' }}>
            <strong>Click to upload</strong> or drag and drop
          </p>
          <p style={{ margin: 0, color: '#6b7280', fontSize: '14px' }}>
            PNG, JPG, GIF up to 10MB each
          </p>
          <p style={{ margin: '10px 0 0 0', color: '#6b7280', fontSize: '12px' }}>
            Select multiple files - upload order will be preserved
          </p>
        </label>
      </div>

      {validationError && (
        <div style={{
          marginTop: '10px',
          padding: '10px',
          backgroundColor: '#fee2e2',
          borderRadius: '6px',
          color: '#dc2626',
          fontSize: '14px'
        }}>
          {validationError}
        </div>
      )}

      {selectedFiles.length > 0 && (
        <div style={{ marginTop: '20px' }}>
          <h3 style={{ margin: '0 0 10px 0', color: '#374151', fontSize: '16px' }}>
            Selected Files ({selectedFiles.length}):
          </h3>
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            marginBottom: '15px'
          }}>
            {selectedFiles.map((file, index) => (
              <div
                key={`${file.name}-${index}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '10px',
                  backgroundColor: '#f3f4f6',
                  borderRadius: '6px',
                  fontSize: '14px'
                }}
              >
                <span style={{ marginRight: '10px' }}>🖼️</span>
                <span style={{ flex: 1 }}>{file.name}</span>
                <span style={{ color: '#6b7280', fontSize: '12px' }}>
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </span>
              </div>
            ))}
          </div>
          
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={handleSubmit}
              disabled={isLoading}
              style={{
                padding: '10px 20px',
                backgroundColor: isLoading ? '#9ca3af' : '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: isLoading ? 'not-allowed' : 'pointer',
                fontSize: '16px',
                fontWeight: '500'
              }}
            >
              {isLoading ? 'Processing...' : 'Extract Text'}
            </button>
            
            <button
              onClick={clearFiles}
              disabled={isLoading}
              style={{
                padding: '10px 20px',
                backgroundColor: '#f3f4f6',
                color: '#374151',
                border: 'none',
                borderRadius: '6px',
                cursor: isLoading ? 'not-allowed' : 'pointer',
                fontSize: '16px'
              }}
            >
              Clear
            </button>
          </div>
        </div>
      )}
    </div>
  );
}