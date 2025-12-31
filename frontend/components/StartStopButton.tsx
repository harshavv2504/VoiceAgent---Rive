
import React from 'react';
import { RecordingState } from '../types';

const Spinner = () => (
    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
    </svg>
);

const StopIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6 mr-2">
        <path fillRule="evenodd" d="M4.5 7.5a3 3 0 0 1 3-3h9a3 3 0 0 1 3 3v9a3 3 0 0 1-3-3h-9a3 3 0 0 1-3-3v-9Z" clipRule="evenodd" />
    </svg>
);

interface StartStopButtonProps {
  recordingState: RecordingState;
  onClick: () => void;
}

export const StartStopButton: React.FC<StartStopButtonProps> = ({ recordingState, onClick }) => {
  const baseClasses = "flex items-center justify-center rounded-full shadow-lg outline-none focus:outline-none focus:ring-4 transition-all duration-300 ease-in-out font-semibold text-lg px-8 py-4 w-48";
  
  let content: React.ReactNode;
  let colorClasses: string;

  const isDisabled = recordingState === RecordingState.PROCESSING || recordingState === RecordingState.REQUESTING_PERMISSION;

  switch (recordingState) {
    case RecordingState.LISTENING:
      colorClasses = "bg-red-600 hover:bg-red-700 focus:ring-red-500/50 text-white";
      content = (
          <>
              <StopIcon />
              <span>Stop</span>
          </>
      );
      break;
    case RecordingState.PROCESSING:
    case RecordingState.REQUESTING_PERMISSION:
      colorClasses = "bg-gray-600 border-gray-600 cursor-not-allowed text-white";
      content = (
          <>
              <Spinner />
              <span>Processing...</span>
          </>
      );
      break;
    case RecordingState.ERROR:
       colorClasses = "bg-blue-600 hover:bg-blue-700 focus:ring-blue-500/50 text-white";
       content = (
           <>
               <span>Try Again</span>
           </>
       );
       break;
    case RecordingState.IDLE:
    default:
      colorClasses = "bg-blue-600 hover:bg-blue-700 focus:ring-blue-500/50 text-white";
      content = (
        <>
            <span>Start</span>
        </>
      );
      break;
  }

  return (
    <button
      onClick={onClick}
      disabled={isDisabled}
      className={`${baseClasses} ${colorClasses}`}
      aria-label={recordingState === RecordingState.LISTENING ? "Stop recording" : "Start recording"}
    >
      {content}
    </button>
  );
};
