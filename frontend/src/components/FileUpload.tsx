import React, { useState, useCallback, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, X, FileText, Image, AlertCircle, CheckCircle, Sparkles } from 'lucide-react';
import ApiService from '../services/api';
import { UploadResponse } from '../types/api';

interface FileUploadProps {
  onUploadSuccess: (response: UploadResponse) => void;
  onUploadError: (error: string) => void;
  disabled?: boolean;
}

const FileUpload: React.FC<FileUploadProps> = ({
  onUploadSuccess,
  onUploadError,
  disabled = false
}) => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadingFileName, setUploadingFileName] = useState<string>('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = useCallback(async (file: File) => {
    setValidationError(null);
    
    // Validate file
    const validation = ApiService.validateFile(file);
    if (!validation.valid) {
      setValidationError(validation.error!);
      onUploadError(validation.error!);
      return;
    }

    setIsUploading(true);
    setUploadingFileName(file.name);
    setUploadProgress(0);

    try {
      // Simulate upload progress for better UX
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + Math.random() * 15;
        });
      }, 300);

      const response = await ApiService.uploadDocument(file);
      
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      // Keep the loading state visible a bit longer for smooth transition
      setTimeout(() => {
        onUploadSuccess(response);
      }, 500);
    } catch (error: any) {
      const errorMessage = error.message || 'Upload fehlgeschlagen';
      setValidationError(errorMessage);
      onUploadError(errorMessage);
      setIsUploading(false);
      setUploadProgress(0);
      setUploadingFileName('');
    }
  }, [onUploadSuccess, onUploadError]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      handleFileUpload(acceptedFiles[0]);
    }
  }, [handleFileUpload]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    disabled: disabled || isUploading,
    maxFiles: 1,
    accept: {
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png']
    },
    noClick: false,
    noKeyboard: false
  });



  const getFileIcon = (fileName: string) => {
    const extension = fileName.split('.').pop()?.toLowerCase();
    if (extension === 'pdf') {
      return <FileText className="w-8 h-8 text-error-500" />;
    } else if (['jpg', 'jpeg', 'png'].includes(extension || '')) {
      return <Image className="w-8 h-8 text-accent-500" />;
    }
    return <FileText className="w-8 h-8 text-primary-500" />;
  };



  const handleClick = () => {
    if (fileInputRef.current && !disabled && !isUploading) {
      fileInputRef.current.click();
    }
  };

  return (
    <div className="space-y-6">
      {/* Upload Loading Overlay - Shows during upload */}
      {isUploading && (
        <div className="fixed inset-0 z-50 bg-white/95 backdrop-blur-sm flex items-center justify-center animate-fade-in">
          <div className="max-w-md w-full mx-4">
            <div className="card-elevated p-8 space-y-6">
              {/* Upload Icon with Animation */}
              <div className="flex justify-center">
                <div className="relative">
                  <div className="w-20 h-20 bg-gradient-to-br from-brand-500 to-brand-600 rounded-3xl flex items-center justify-center animate-pulse-soft">
                    <Upload className="w-10 h-10 text-white" />
                  </div>
                  <div className="absolute -bottom-2 -right-2 w-8 h-8 bg-gradient-to-br from-accent-500 to-accent-600 rounded-full flex items-center justify-center animate-spin-slow">
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  </div>
                </div>
              </div>

              {/* Upload Status Text */}
              <div className="text-center space-y-2">
                <h3 className="text-2xl font-bold text-primary-900">
                  Datei wird hochgeladen
                </h3>
                <p className="text-primary-600">
                  {uploadingFileName && (
                    <span className="font-medium">{uploadingFileName}</span>
                  )}
                </p>
                <p className="text-sm text-primary-500">
                  Bitte warten Sie einen Moment...
                </p>
              </div>

              {/* Progress Bar */}
              <div className="space-y-2">
                <div className="w-full bg-neutral-100 rounded-full h-2 overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-brand-500 to-accent-500 rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
                <p className="text-center text-xs text-primary-500">
                  {Math.round(uploadProgress)}% hochgeladen
                </p>
              </div>

              {/* Info Text */}
              <div className="text-center">
                <p className="text-xs text-primary-500">
                  {uploadProgress < 30 && "Verbindung wird hergestellt..."}
                  {uploadProgress >= 30 && uploadProgress < 60 && "Datei wird übertragen..."}
                  {uploadProgress >= 60 && uploadProgress < 90 && "Fast fertig..."}
                  {uploadProgress >= 90 && "Verarbeitung wird vorbereitet..."}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Regular Upload Area - Hidden during upload */}
      <div
        {...getRootProps()}
        onClick={handleClick}
        className={`upload-area ${isDragActive ? 'dragover' : ''} ${disabled || isUploading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'} ${isUploading ? 'pointer-events-none' : ''}`}
        style={{ display: isUploading ? 'none' : 'block' }}
      >
        <input {...getInputProps()} ref={fileInputRef} />
        
        <div className="space-y-6">
          <div className="flex justify-center">
            <div className={`group w-16 h-16 bg-gradient-to-br from-brand-500 to-brand-600 rounded-2xl flex items-center justify-center transition-all duration-300 ${!disabled ? 'group-hover:scale-110 group-hover:shadow-glow' : ''}`}>
              <Upload className="w-8 h-8 text-white transition-transform duration-300 group-hover:scale-110" />
            </div>
          </div>

          <div className="text-center space-y-3">
            <h3 className="text-2xl font-bold text-primary-900">
              {isDragActive
                ? 'Datei hier ablegen'
                : 'Dokument hochladen'
              }
            </h3>
            
            <p className="text-primary-600 text-lg leading-relaxed max-w-md mx-auto">
              {isDragActive 
                ? 'Lassen Sie die Datei los, um sie hochzuladen'
                : 'Ziehen Sie eine Datei hierher oder klicken Sie zum Auswählen'
              }
            </p>
          </div>

          {!isUploading && (
            <div className="flex justify-center">
              <div className="glass-effect px-6 py-3 rounded-xl">
                <div className="text-sm text-primary-600 space-y-1 text-center">
                  <div className="font-semibold">Unterstützte Formate</div>
                  <div className="flex items-center justify-center space-x-4 text-xs">
                    <span className="flex items-center space-x-1">
                      <FileText className="w-3 h-3 text-error-500" />
                      <span>PDF</span>
                    </span>
                    <span className="flex items-center space-x-1">
                      <Image className="w-3 h-3 text-accent-500" />
                      <span>JPG, PNG</span>
                    </span>
                    <span className="text-primary-400">• Max. 50 MB</span>
                  </div>
                </div>
              </div>
            </div>
          )}


        </div>
      </div>

      {/* Validation Error */}
      {validationError && (
        <div className="card-elevated border-error-200/50 bg-gradient-to-br from-error-50/50 to-white animate-slide-up">
          <div className="card-compact">
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-error-500 to-error-600 rounded-xl flex items-center justify-center">
                <AlertCircle className="w-5 h-5 text-white" />
              </div>
              <div className="flex-1">
                <h4 className="font-semibold text-error-900 mb-1">Upload fehlgeschlagen</h4>
                <p className="text-error-700 text-sm leading-relaxed">{validationError}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Success State (if needed) */}
      {!validationError && !isUploading && (
        <div className="text-center">
          <p className="text-xs text-primary-500">
            Ihre Daten werden DSGVO-konform verarbeitet und nicht gespeichert
          </p>
        </div>
      )}
    </div>
  );
};

export default FileUpload; 