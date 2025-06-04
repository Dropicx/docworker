import React, { useState, useCallback, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Camera, X, FileText, Image, AlertCircle, CheckCircle, Sparkles } from 'lucide-react';
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
  const [validationError, setValidationError] = useState<string | null>(null);
  const [showCamera, setShowCamera] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);

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

    try {
      const response = await ApiService.uploadDocument(file);
      onUploadSuccess(response);
    } catch (error: any) {
      const errorMessage = error.message || 'Upload fehlgeschlagen';
      setValidationError(errorMessage);
      onUploadError(errorMessage);
    } finally {
      setIsUploading(false);
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
    }
  });

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' } // Bevorzugt Rückkamera auf Handys
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
      
      setCameraStream(stream);
      setShowCamera(true);
    } catch (error) {
      console.error('Kamera-Zugriff fehlgeschlagen:', error);
      onUploadError('Kamera-Zugriff nicht möglich. Bitte überprüfen Sie die Berechtigungen.');
    }
  };

  const stopCamera = () => {
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop());
      setCameraStream(null);
    }
    setShowCamera(false);
  };

  const capturePhoto = () => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      const context = canvas.getContext('2d');

      if (context) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0);

        canvas.toBlob((blob) => {
          if (blob) {
            const file = new File([blob], `document-${Date.now()}.png`, {
              type: 'image/png'
            });
            handleFileUpload(file);
            stopCamera();
          }
        }, 'image/png', 0.9);
      }
    }
  };

  const getFileIcon = (fileName: string) => {
    const extension = fileName.split('.').pop()?.toLowerCase();
    if (extension === 'pdf') {
      return <FileText className="w-8 h-8 text-error-500" />;
    } else if (['jpg', 'jpeg', 'png'].includes(extension || '')) {
      return <Image className="w-8 h-8 text-accent-500" />;
    }
    return <FileText className="w-8 h-8 text-primary-500" />;
  };

  if (showCamera) {
    return (
      <div className="card-elevated animate-scale-in">
        <div className="card-body">
          <div className="flex justify-between items-center mb-6">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-brand-500 to-brand-600 rounded-xl flex items-center justify-center">
                <Camera className="w-5 h-5 text-white" />
              </div>
              <h3 className="text-xl font-bold text-primary-900">
                Dokument fotografieren
              </h3>
            </div>
            <button
              onClick={stopCamera}
              className="p-2 text-primary-400 hover:text-primary-600 hover:bg-primary-50 rounded-xl transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="relative overflow-hidden rounded-2xl bg-primary-900 shadow-medium">
            <video
              ref={videoRef}
              className="w-full aspect-video object-cover"
              autoPlay
              playsInline
              muted
            />
            <canvas ref={canvasRef} className="hidden" />
            
            {/* Camera Overlay */}
            <div className="absolute inset-0 pointer-events-none">
              <div className="absolute inset-4 border-2 border-white/50 rounded-xl"></div>
              <div className="absolute top-4 left-4 right-4 flex justify-between">
                <div className="glass-effect px-3 py-1 rounded-lg">
                  <span className="text-xs font-medium text-white">Dokument im Rahmen positionieren</span>
                </div>
                <div className="glass-effect px-2 py-1 rounded-lg">
                  <div className="w-2 h-2 bg-success-400 rounded-full animate-pulse-soft"></div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 flex gap-3">
            <button
              onClick={capturePhoto}
              className="btn-primary flex-1"
              disabled={isUploading}
            >
              {isUploading ? (
                <>
                  <div className="loading-spinner mr-2" />
                  Wird verarbeitet...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5 mr-2" />
                  Foto aufnehmen
                </>
              )}
            </button>
            <button
              onClick={stopCamera}
              className="btn-secondary px-6"
            >
              Abbrechen
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Upload Area */}
      <div
        {...getRootProps()}
        className={`upload-area ${isDragActive ? 'dragover' : ''} ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'} ${isUploading ? 'pointer-events-none' : ''}`}
      >
        <input {...getInputProps()} />
        
        <div className="space-y-6">
          <div className="flex justify-center">
            {isUploading ? (
              <div className="relative">
                <div className="w-16 h-16 bg-gradient-to-br from-brand-500 to-brand-600 rounded-2xl flex items-center justify-center animate-pulse-soft">
                  <Upload className="w-8 h-8 text-white" />
                </div>
                <div className="absolute -bottom-1 -right-1 w-6 h-6 bg-gradient-to-br from-accent-500 to-accent-600 rounded-full flex items-center justify-center">
                  <div className="loading-spinner w-3 h-3 text-white" />
                </div>
              </div>
            ) : (
              <div className={`group w-16 h-16 bg-gradient-to-br from-brand-500 to-brand-600 rounded-2xl flex items-center justify-center transition-all duration-300 ${!disabled ? 'group-hover:scale-110 group-hover:shadow-glow' : ''}`}>
                <Upload className="w-8 h-8 text-white transition-transform duration-300 group-hover:scale-110" />
              </div>
            )}
          </div>

          <div className="text-center space-y-3">
            <h3 className="text-2xl font-bold text-primary-900">
              {isUploading
                ? 'Datei wird hochgeladen...'
                : isDragActive
                ? 'Datei hier ablegen'
                : 'Dokument hochladen'
              }
            </h3>
            
            {!isUploading && (
              <p className="text-primary-600 text-lg leading-relaxed max-w-md mx-auto">
                {isDragActive 
                  ? 'Lassen Sie die Datei los, um sie hochzuladen'
                  : 'Ziehen Sie eine Datei hierher oder klicken Sie zum Auswählen'
                }
              </p>
            )}
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
                    <span className="text-primary-400">• Max. 10 MB</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Camera Button */}
      {!isUploading && (
        <div className="flex justify-center">
          <button
            onClick={startCamera}
            className="btn-secondary group"
            disabled={disabled}
          >
            <Camera className="w-5 h-5 mr-2 transition-transform duration-200 group-hover:scale-110" />
            <span>Mit Kamera fotografieren</span>
          </button>
        </div>
      )}

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