import React, { useState, useCallback, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Camera, X, FileText, Image, AlertCircle, CheckCircle } from 'lucide-react';
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
      return <FileText className="w-8 h-8 text-red-500" />;
    } else if (['jpg', 'jpeg', 'png'].includes(extension || '')) {
      return <Image className="w-8 h-8 text-blue-500" />;
    }
    return <FileText className="w-8 h-8 text-gray-500" />;
  };

  if (showCamera) {
    return (
      <div className="card animate-slide-up">
        <div className="card-body">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Dokument fotografieren
            </h3>
            <button
              onClick={stopCamera}
              className="p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="relative">
            <video
              ref={videoRef}
              className="w-full rounded-lg bg-black"
              autoPlay
              playsInline
              muted
            />
            <canvas ref={canvasRef} className="hidden" />
          </div>

          <div className="mt-4 flex gap-2">
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
                  <Camera className="w-5 h-5 mr-2" />
                  Foto aufnehmen
                </>
              )}
            </button>
            <button
              onClick={stopCamera}
              className="btn-secondary"
            >
              Abbrechen
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Upload Area */}
      <div
        {...getRootProps()}
        className={`upload-area ${isDragActive ? 'dragover' : ''} ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
      >
        <input {...getInputProps()} />
        
        <div className="space-y-4">
          <div className="flex justify-center">
            {isUploading ? (
              <div className="loading-spinner w-12 h-12 text-medical-600" />
            ) : (
              <Upload className="w-12 h-12 text-gray-400" />
            )}
          </div>

          <div className="text-center">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              {isUploading
                ? 'Datei wird hochgeladen...'
                : isDragActive
                ? 'Datei hier ablegen'
                : 'Medizinisches Dokument hochladen'
              }
            </h3>
            
            {!isUploading && (
              <p className="text-gray-600">
                Ziehen Sie eine Datei hierher oder klicken Sie zum Auswählen
              </p>
            )}
          </div>

          {!isUploading && (
            <div className="flex justify-center">
              <div className="text-sm text-gray-500 space-y-1">
                <div>Unterstützte Formate: PDF, JPG, PNG</div>
                <div>Maximale Größe: 10 MB</div>
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
            className="btn-secondary flex items-center space-x-2"
            disabled={disabled}
          >
            <Camera className="w-5 h-5" />
            <span>Mit Kamera fotografieren</span>
          </button>
        </div>
      )}

      {/* Validation Error */}
      {validationError && (
        <div className="flex items-center p-4 bg-error-50 border border-error-200 rounded-lg animate-slide-up">
          <AlertCircle className="w-5 h-5 text-error-600 mr-3 flex-shrink-0" />
          <div className="text-error-700 text-sm">{validationError}</div>
        </div>
      )}

      {/* Upload Success Indicator */}
      {!validationError && !isUploading && (
        <div className="text-center">
          <div className="inline-flex items-center text-sm text-gray-500">
            <CheckCircle className="w-4 h-4 mr-2 text-success-500" />
            Bereit für Upload
          </div>
        </div>
      )}
    </div>
  );
};

export default FileUpload; 