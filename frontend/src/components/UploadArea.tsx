'use client';

import { useCallback, useState } from 'react';
import { logger } from '@/lib/logger';

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
    logger.debug('Validating file', { 
      name: file.name, 
      type: file.type, 
      size: file.size 
    });
    
    if (!ALLOWED_TYPES.includes(file.type)) {
      const error = `${file.name}: Invalid file type. Allowed: PNG, JPG, GIF, BMP, TIFF, WEBP`;
      logger.warn('File validation failed - invalid type', { 
        filename: file.name, 
        fileType: file.type 
      });
      return error;
    }
    if (file.size > MAX_FILE_SIZE) {
      const error = `${file.name}: File too large (max 10MB)`;
      logger.warn('File validation failed - too large', { 
        filename: file.name, 
        size: file.size, 
        maxSize: MAX_FILE_SIZE 
      });
      return error;
    }
    
    logger.debug('File validation passed', { filename: file.name });
    return null;
  };

  const handleFiles = useCallback((files: FileList | null) => {
    if (!files) {
      logger.debug('handleFiles called with null files');
      return;
    }

    logger.info('Files selected', { count: files.length });
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

    logger.info('All files validated successfully', { 
      count: fileArray.length,
      files: fileArray.map(f => ({ name: f.name, size: f.size }))
    });
    
    setSelectedFiles(fileArray);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
    logger.debug('Drag over upload area');
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    logger.debug('Drag left upload area');
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    logger.info('Files dropped', { count: e.dataTransfer.files.length });
    handleFiles(e.dataTransfer.files);
  }, [handleFiles]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    logger.info('Files selected via input', { count: e.target.files?.length || 0 });
    handleFiles(e.target.files);
  }, [handleFiles]);

  const handleSubmit = useCallback(() => {
    if (selectedFiles.length > 0) {
      logger.info('Extract text button clicked', { 
        fileCount: selectedFiles.length,
        files: selectedFiles.map(f => f.name)
      });
      onFilesSelected(selectedFiles);
    } else {
      logger.warn('Extract text clicked but no files selected');
    }
  }, [selectedFiles, onFilesSelected]);

  const clearFiles = useCallback(() => {
    logger.info('Clear button clicked', { clearedCount: selectedFiles.length });
    setSelectedFiles([]);
    setValidationError('');
  }, [selectedFiles.length]);

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