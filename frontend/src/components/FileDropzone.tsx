import React, { useCallback, useState, useRef } from 'react';
import './FileDropzone.css';

interface FileDropzoneProps {
  onFileSelect: (file: File) => void;
  accept?: string;
  maxSizeMB?: number;
}

const FileDropzone: React.FC<FileDropzoneProps> = ({
  onFileSelect,
  accept = '.pdf,.txt',
  maxSizeMB = 10,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateFile = useCallback(
    (file: File): boolean => {
      setError(null);
      const validExtensions = accept.split(',').map((ext) => ext.trim().toLowerCase());
      const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
      if (!validExtensions.includes(fileExt)) {
        setError(`Invalid file type. Accepted: ${accept}`);
        return false;
      }
      if (file.size > maxSizeMB * 1024 * 1024) {
        setError(`File too large. Maximum size is ${maxSizeMB}MB.`);
        return false;
      }
      return true;
    },
    [accept, maxSizeMB]
  );

  const handleFile = useCallback(
    (file: File) => {
      if (validateFile(file)) {
        setSelectedFile(file);
        onFileSelect(file);
      }
    },
    [validateFile, onFileSelect]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleClick = () => {
    inputRef.current?.click();
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div
      className={`file-dropzone ${isDragging ? 'file-dropzone--dragging' : ''} ${selectedFile ? 'file-dropzone--selected' : ''}`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={handleClick}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        onChange={handleInputChange}
        className="file-dropzone__input"
      />

      {selectedFile ? (
        <div className="file-dropzone__selected">
          <span className="file-dropzone__file-icon">📄</span>
          <div className="file-dropzone__file-info">
            <span className="file-dropzone__file-name">{selectedFile.name}</span>
            <span className="file-dropzone__file-size">
              {formatSize(selectedFile.size)}
            </span>
          </div>
        </div>
      ) : (
        <div className="file-dropzone__placeholder">
          <span className="file-dropzone__upload-icon">📁</span>
          <p className="file-dropzone__text">
            <strong>Drop your file here</strong> or click to browse
          </p>
          <p className="file-dropzone__hint">
            Supports PDF and TXT files (max {maxSizeMB}MB)
          </p>
        </div>
      )}

      {error && <p className="file-dropzone__error">{error}</p>}
    </div>
  );
};

export default FileDropzone;
