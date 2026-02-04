import React from 'react';

interface CaptureButtonProps {
  onCapture: () => void;
  autoProgress: number; // 0-1, fraction of auto-capture timer elapsed
  disabled?: boolean;
}

const RADIUS = 36;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

const CaptureButton: React.FC<CaptureButtonProps> = ({ onCapture, autoProgress, disabled }) => {
  const dashOffset = CIRCUMFERENCE * (1 - autoProgress);

  return (
    <button
      onClick={onCapture}
      disabled={disabled}
      className="relative w-[80px] h-[80px] flex items-center justify-center focus:outline-none disabled:opacity-50"
      aria-label="Foto aufnehmen"
    >
      {/* Progress ring */}
      <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 80 80">
        {/* Background ring */}
        <circle
          cx="40"
          cy="40"
          r={RADIUS}
          fill="none"
          stroke="rgba(255,255,255,0.3)"
          strokeWidth="4"
        />
        {/* Progress arc */}
        {autoProgress > 0 && (
          <circle
            cx="40"
            cy="40"
            r={RADIUS}
            fill="none"
            stroke="#22c55e"
            strokeWidth="4"
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={dashOffset}
            className="transition-[stroke-dashoffset] duration-100"
          />
        )}
      </svg>
      {/* Inner shutter circle */}
      <div className="w-[60px] h-[60px] rounded-full bg-white border-4 border-white/80 shadow-lg active:scale-90 transition-transform" />
    </button>
  );
};

export default CaptureButton;
