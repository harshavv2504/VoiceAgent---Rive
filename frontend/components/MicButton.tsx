import React from 'react';

interface MicButtonProps {
  isMuted: boolean;
  isListening: boolean;
  onClick: () => void;
}

const MicIcon = ({ isMuted, isListening }: { isMuted: boolean, isListening: boolean }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
    className={`w-6 h-6 transition-transform duration-300 ${isListening && !isMuted ? 'animate-pulse-subtle' : ''}`}
  >
    <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5a3.75 3.75 0 1 1 7.5 0v8.25a3.75 3.75 0 1 1-7.5 0V4.5Z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M6 10.5a.75.75 0 0 1 .75.75v1.5a5.25 5.25 0 1 0 10.5 0v-1.5a.75.75 0 0 1 1.5 0v1.5a6.75 6.75 0 1 1-13.5 0v-1.5A.75.75 0 0 1 6 10.5Z" />
    {isMuted && <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.25 18.75 18.75" />}
  </svg>
);


export const MicButton: React.FC<MicButtonProps> = ({ isMuted, isListening, onClick }) => {
  const baseClasses = "relative flex items-center justify-center rounded-full shadow-lg outline-none focus:outline-none focus:ring-4 transition-all duration-300 ease-in-out border-2 w-16 h-16";
  
  let colorClasses: string;

  if (isListening) {
    if (isMuted) {
      colorClasses = "bg-transparent border-red-600 hover:bg-red-600/20 focus:ring-red-500/50 text-white";
    } else {
      colorClasses = "bg-transparent border-blue-600 hover:bg-blue-600/20 focus:ring-blue-500/50 text-white";
    }
  } else {
      colorClasses = "bg-transparent border-gray-600 text-gray-400 cursor-not-allowed";
  }

  return (
    <div className="relative flex items-center justify-center w-16 h-16">
      {isListening && (
        <>
          <div className="absolute w-16 h-16 bg-blue-500/50 rounded-full animate-ping-slow"></div>
          <div className="absolute w-16 h-16 bg-blue-500/30 rounded-full animate-ping-medium"></div>
        </>
      )}
      <button
        onClick={onClick}
        disabled={!isListening}
        className={`${baseClasses} ${colorClasses}`}
        aria-label={isMuted ? "Unmute microphone" : "Mute microphone"}
      >
        <MicIcon isMuted={isMuted} isListening={isListening} />
      </button>
    </div>
  );
};