import React, { useState, useRef, useEffect } from 'react';

const GearIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
    <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-1.57 1.996A1.532 1.532 0 013.17 7.49c-1.56.38-1.56 2.6 0 2.98a1.532 1.532 0 01.948 2.286c-.836 1.372.734 2.942 1.996 1.57a1.532 1.532 0 012.286.948c.38 1.56 2.6 1.56 2.98 0a1.532 1.532 0 012.286-.948c1.372.836 2.942-.734 1.57-1.996A1.532 1.532 0 0116.83 12.51c1.56-.38 1.56-2.6 0-2.98a1.532 1.532 0 01-.948-2.286c.836-1.372-.734-2.942-1.996-1.57A1.532 1.532 0 0111.49 3.17zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
  </svg>
);

interface AudioDeviceSelectorProps {
  devices: MediaDeviceInfo[];
  selectedDeviceId: string;
  onDeviceSelect: (deviceId: string) => void;
}

export const AudioDeviceSelector: React.FC<AudioDeviceSelectorProps> = ({ devices, selectedDeviceId, onDeviceSelect }) => {
  const [isOpen, setIsOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const selectedDevice = devices.find(d => d.deviceId === selectedDeviceId) || devices[0];

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (devices.length < 2) {
    return null;
  }

  return (
    <div ref={wrapperRef} className="absolute bottom-6 right-6 z-20">
      <div className="relative">
        {isOpen && (
          <div className="absolute bottom-full mb-2 w-72 origin-bottom-right rounded-lg bg-white/10 border border-white/20 backdrop-blur-md shadow-lg">
            <ul className="p-1">
              {devices.map((device, index) => (
                <li key={device.deviceId}>
                  <button
                    onClick={() => {
                      onDeviceSelect(device.deviceId);
                      setIsOpen(false);
                    }}
                    className={`w-full text-left px-3 py-2 text-sm rounded-md transition-colors duration-150 ${selectedDeviceId === device.deviceId ? 'bg-blue-500/50 text-white' : 'text-gray-200 hover:bg-white/20'}`}
                  >
                    {device.label || `Microphone ${index + 1}`}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 backdrop-blur-sm px-4 py-2 text-white shadow-lg transition-colors duration-200"
          aria-haspopup="true"
          aria-expanded={isOpen}
        >
          <GearIcon />
          <span className="text-sm truncate max-w-48">{selectedDevice?.label || `Default Microphone`}</span>
        </button>
      </div>
    </div>
  );
};