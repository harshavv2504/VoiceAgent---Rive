import React, { useState, useEffect, useCallback, useRef } from 'react';
import { StartStopButton } from './components/StartStopButton';
import { MicButton } from './components/MicButton';
import { ParticleBackground } from './components/ParticleBackground';
import { AudioDeviceSelector } from './components/AudioDeviceSelector';
import { Avatar } from './components/Avatar';
import { RecordingState, WebSocketState } from './types';
import { useWebSocket } from './hooks/useWebSocket';
import { useAudioRecorder } from './hooks/useAudioRecorder';

const App: React.FC = () => {
    const [audioDevices, setAudioDevices] = useState<MediaDeviceInfo[]>([]);
    const [selectedDeviceId, setSelectedDeviceId] = useState<string>('default');
    
    // The placeholder text is now more descriptive.
    const [displayText, setDisplayText] = useState<string>("The agent's response will appear here once connected...");

    // Voice agent state
    const [isVoiceAgentRunning, setIsVoiceAgentRunning] = useState(false);
    const [isAudioPlaying, setIsAudioPlaying] = useState(false);

    // Debug audio state changes
    useEffect(() => {
        console.log(`🔊 isAudioPlaying state changed to: ${isAudioPlaying}`);
    }, [isAudioPlaying]);
    
    // Audio playback refs (exact same as FastAPI frontend)
    const audioContextRef = useRef<AudioContext | null>(null);
    const audioOutputContextRef = useRef<AudioContext | null>(null);
    const nextPlayTimeRef = useRef<number>(0);
    const audioOutputSampleRateRef = useRef<number>(16000);
    const lastSeqRef = useRef<number>(-1);
    const audioTimeoutIdRef = useRef<NodeJS.Timeout | null>(null);

    // Audio playback functions
    const initAudioContext = useCallback(() => {
        if (!audioContextRef.current) {
            audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
        }
        return audioContextRef.current;
    }, []);


    // Function to play audio output received from the server (exact copy from FastAPI)
    const playAudioOutput = useCallback((audioData: string, sampleRate: number) => {
        try {
            // Create audio context if it doesn't exist
            if (!audioOutputContextRef.current) {
                audioOutputContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
                // Initialize nextPlayTime to current audio context time
                nextPlayTimeRef.current = audioOutputContextRef.current.currentTime;
            }
            
            // Update sample rate if provided
            if (sampleRate) {
                audioOutputSampleRateRef.current = sampleRate;
            }
            
            // Decode base64 audio data to binary (exact same as FastAPI)
            const binaryString = atob(audioData);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            
            // Convert the binary audio data to Int16Array (raw PCM format from server)
            const pcmData = new Int16Array(bytes.buffer);
            const floatData = new Float32Array(pcmData.length);
            
            // Convert 16-bit PCM to float32 (-1.0 to 1.0)
            for (let i = 0; i < pcmData.length; i++) {
                floatData[i] = pcmData[i] / 32768.0;
            }
            
            // Create an audio buffer with the correct sample rate
            const audioBuffer = audioOutputContextRef.current.createBuffer(1, floatData.length, audioOutputSampleRateRef.current);
            audioBuffer.getChannelData(0).set(floatData);
            
            // Set audio playing to true when we start playing
            setIsAudioPlaying(true);
            
            // Clear any existing timeout since we have new audio
            if (audioTimeoutIdRef.current) {
                clearTimeout(audioTimeoutIdRef.current);
                audioTimeoutIdRef.current = null;
            }
            
            // Schedule the audio buffer for seamless playback
            scheduleAudioBuffer(audioBuffer);
            
        } catch (err) {
            console.error('Error processing audio output:', err);
            setIsAudioPlaying(false);
        }
    }, []);

    // Schedule audio buffer for seamless playback (exact copy from FastAPI)
    const scheduleAudioBuffer = useCallback((audioBuffer: AudioBuffer) => {
        try {
            // Create audio source
            const source = audioOutputContextRef.current!.createBufferSource();
            source.buffer = audioBuffer;
            
            // Add a gain node for volume control
            const gainNode = audioOutputContextRef.current!.createGain();
            gainNode.gain.value = 1.0; // Full volume
            
            // Connect the audio graph
            source.connect(gainNode);
            gainNode.connect(audioOutputContextRef.current!.destination);
            
            // Calculate when this chunk should start playing (exact same as FastAPI)
            const currentTime = audioOutputContextRef.current!.currentTime;
            const bufferDuration = audioBuffer.duration;
            
            // If nextPlayTime is in the past or too close to current time, move it slightly ahead
            if (nextPlayTimeRef.current <= currentTime + 0.03) {
                nextPlayTimeRef.current = currentTime + 0.03; // Small buffer to prevent glitches
            }
            
            // Schedule the audio to start at the calculated time
            source.start(nextPlayTimeRef.current);
            
            // Update nextPlayTime for the next chunk
            nextPlayTimeRef.current += bufferDuration;
            
            // Set up event listener to detect when this audio chunk finishes (exact same as FastAPI)
            source.onended = function() {
                // Check if this was the last scheduled audio chunk
                const timeUntilNext = nextPlayTimeRef.current - audioOutputContextRef.current!.currentTime;
                if (timeUntilNext <= 0.1) { // If no more audio scheduled soon
                    // Set a timeout to detect if no more audio comes in
                    audioTimeoutIdRef.current = setTimeout(() => {
                        setIsAudioPlaying(false);
                        audioTimeoutIdRef.current = null;
                    }, 200); // Wait 200ms for more audio to arrive
                }
            };
            
        } catch (err) {
            console.error('Error scheduling audio buffer:', err);
            setIsAudioPlaying(false);
        }
    }, []);


    // This function handles parsed JSON messages from the backend
    const handleWebSocketMessage = useCallback((data: any) => {
        console.log('Received WebSocket message:', data);
        
        // Handle different message types from the backend
        if (typeof data === 'string') {
            // Fallback for non-JSON messages
            setDisplayText(data);
            return;
        }

        // Handle JSON messages
        if (data.type === 'conversation_update' && data.data) {
            // Only show assistant messages, skip user messages
            if (data.data.role === 'assistant') {
                console.log('Displaying assistant message:', data.data.content);
                setDisplayText(data.data.content);
            }
        } else if (data.type === 'voice_agent_stopped') {
            // Handle voice agent stopped
            setIsVoiceAgentRunning(false);
            setDisplayText("Voice agent stopped. Click 'Start' to begin again.");
        } else if (data.type === 'audio_output') {
            // Handle audio output from backend (exact same as FastAPI frontend)
            console.log('Received audio output:', data.seq);
            if (data.audio && data.sampleRate) {
                // Use the exact same audio handling as FastAPI frontend
                playAudioOutput(data.audio, data.sampleRate);
            }
        } else {
            // For any other message types, show a generic message
            console.log('Unknown message type:', data.type, 'Full data:', data);
            setDisplayText(`Received message type: ${data.type}`);
        }
    }, [setDisplayText, setIsVoiceAgentRunning, playAudioOutput]);

    // The onMessage callback is now passed to the hook.
    const { connectionState, toggleConnection, sendMessage } = useWebSocket({
      onMessage: handleWebSocketMessage,
    });

    // Audio data handler for WebSocket transmission (exact same as FastAPI)
    const handleAudioData = useCallback((audioData: ArrayBuffer, sampleRate: number) => {
        console.log('🎤 Audio data received:', audioData.byteLength, 'bytes, sampleRate:', sampleRate);
        console.log('🎤 Connection state:', connectionState, 'Voice agent running:', isVoiceAgentRunning);
        
        if (connectionState === WebSocketState.OPEN) {
            // Convert to base64 exactly like FastAPI frontend
            const audioBytes = new Uint8Array(audioData);
            const base64Audio = btoa(String.fromCharCode(...audioBytes));
            
            console.log('🎤 Sending audio data to backend...');
            sendMessage({
                type: 'audio_data',
                audio: base64Audio,
                sampleRate: sampleRate
            });
        } else {
            console.log('🎤 Not sending audio - connection not open:', connectionState);
        }
    }, [connectionState, sendMessage]);
    
    const { 
      recordingState, error: recorderError, audioLevel, bassLevel, 
      startRecording, stopRecording, setProcessingState, isMuted, toggleMute 
    } = useAudioRecorder({ selectedDeviceId, onAudioData: handleAudioData });

    // Debug recording state changes
    useEffect(() => {
        console.log('🎤 Recording state changed to:', recordingState);
        if (recorderError) {
            console.error('🎤 Recorder error:', recorderError);
        }
    }, [recordingState, recorderError]);

    // Voice agent control functions
    const startVoiceAgent = useCallback(async () => {
        console.log('Start button clicked!');
        console.log('Connection state:', connectionState);
        console.log('WebSocket state:', WebSocketState.OPEN);
        
        if (connectionState === WebSocketState.OPEN) {
            try {
                // Start recording FIRST (like FastAPI frontend)
                console.log('🎤 Starting audio recording...');
                await startRecording();
                console.log('🎤 startRecording completed successfully');
                
                // Now start the voice agent on the server
                console.log('Sending start_voice_agent message...');
                sendMessage({
                    type: 'start_voice_agent',
                    data: {
                        inputDeviceId: selectedDeviceId,
                        industry: 'deepgram',
                        voiceModel: import.meta.env.VITE_VOICE_MODEL || 'aura-2-thalia-en',
                        voiceName: import.meta.env.VITE_VOICE_NAME || 'Thalia',
                        browserAudio: true
                    }
                });
                
                // Set voice agent running AFTER sending message (like FastAPI)
                setIsVoiceAgentRunning(true);
                setDisplayText("Starting voice agent...");
            } catch (error) {
                console.error('🎤 startRecording failed:', error);
                setDisplayText("Failed to start audio recording. Please check microphone permissions.");
            }
        } else {
            console.log('WebSocket not connected, cannot start voice agent');
            setDisplayText("WebSocket not connected. Please wait...");
        }
    }, [connectionState, selectedDeviceId, sendMessage, startRecording]);

    const stopVoiceAgent = useCallback(() => {
        if (connectionState === WebSocketState.OPEN) {
            sendMessage({
                type: 'stop_voice_agent'
            });
            setIsVoiceAgentRunning(false);
            setDisplayText("Voice agent stopped. Click 'Start' to begin again.");
            // Stop recording when voice agent stops
            stopRecording();
        }
    }, [connectionState, sendMessage, stopRecording]);
    
    useEffect(() => {
      const getAudioDevices = async () => {
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            const audioInputDevices = devices.filter(device => device.kind === 'audioinput');
            setAudioDevices(audioInputDevices);
        // FIX: Added curly braces around the catch block to fix a syntax error that was causing cascading compile errors.
        } catch (e) {
          console.error("Could not enumerate devices.", e);
        }
      };
      
      navigator.mediaDevices.addEventListener('devicechange', getAudioDevices);
      getAudioDevices();
      
      return () => {
          navigator.mediaDevices.removeEventListener('devicechange', getAudioDevices);
      };
    }, []);

    // Remove automatic recording start - let user control it manually
    // useEffect(() => {
    //   if (connectionState === WebSocketState.OPEN && recordingState !== RecordingState.LISTENING) {
    //     startRecording();
    //   } else if (
    //     (connectionState === WebSocketState.CLOSED || connectionState === WebSocketState.ERROR) &&
    //     recordingState === RecordingState.LISTENING
    //   ) {
    //     stopRecording();
    //     const timer = setTimeout(() => setProcessingState(false), 300);
    //     return () => clearTimeout(timer);
    //   }
    // }, [connectionState, recordingState, startRecording, stopRecording, setProcessingState]);

    const handleDeviceSelect = useCallback((deviceId: string) => {
      setSelectedDeviceId(deviceId);
      if (recordingState === RecordingState.LISTENING) {
        stopRecording();
        setTimeout(startRecording, 100);
      }
    // FIX: Added missing dependency `setSelectedDeviceId` to the useCallback hook.
    }, [recordingState, startRecording, stopRecording, setSelectedDeviceId]);
    
    useEffect(() => {
      const style = document.createElement('style');
      style.innerHTML = `
        @keyframes ping-slow { 75%, 100% { transform: scale(1.5); opacity: 0; } }
        @keyframes ping-medium { 75%, 100% { transform: scale(1.8); opacity: 0; } }
        .animate-ping-slow { animation: ping-slow 2s cubic-bezier(0, 0, 0.2, 1) infinite; }
        .animate-ping-medium { animation: ping-medium 2.5s cubic-bezier(0, 0, 0.2, 1) infinite; }
        @keyframes shimmer { 0% { transform: translateX(-100%) skewX(-15deg); } 100% { transform: translateX(100%) skewX(-15deg); } }
        .animate-shimmer::before { content: ''; position: absolute; top: 0; left: 0; width: 50%; height: 100%; background: linear-gradient(to right, rgba(255, 255, 255, 0) 0%, rgba(255, 255, 255, 0.1) 50%, rgba(255, 255, 255, 0) 100%); transform: translateX(-100%) skewX(-15deg); animation: shimmer 4s infinite linear; }
        .hide-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
        .hide-scrollbar::-webkit-scrollbar { display: none; }
        @keyframes pulse-subtle { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.1); } }
        .animate-pulse-subtle { animation: pulse-subtle 2s ease-in-out infinite; }
      `;
      document.head.appendChild(style);
      return () => { document.head.removeChild(style); };
    }, []);

    const getButtonState = (wsState: WebSocketState): RecordingState => {
        switch (wsState) {
            case WebSocketState.CONNECTING:
            case WebSocketState.CLOSING:
                return RecordingState.PROCESSING;
            case WebSocketState.OPEN:
                return RecordingState.LISTENING;
            case WebSocketState.ERROR:
                return RecordingState.ERROR;
            case WebSocketState.CLOSED:
            default:
                return RecordingState.IDLE;
        }
    };
    
  return (
    <div className="relative flex flex-col h-screen w-full bg-gradient-to-br from-blue-950 to-black text-white font-sans overflow-hidden">
        <ParticleBackground audioLevel={isMuted ? 0 : audioLevel} bassLevel={isMuted ? 0 : bassLevel} />
        
        <div className="z-10 flex flex-col h-full w-full">
            <header className="flex-shrink-0 pt-16 text-center">
                <h1 className="text-5xl md:text-6xl text-white tracking-tight font-mono underline">
                    {import.meta.env.VITE_BUSINESS_NAME || 'Bean & Brew Coffee Shop'}
                </h1>
                <p className="mt-8 text-3xl md:text-4xl text-gray-300 font-mono">Voice Agent</p>
                <div className="h-10 mt-4 flex items-center justify-center">
                    {recorderError && <p className="text-yellow-400">{recorderError}</p>}
                </div>
            </header>

            <main className="flex-grow flex flex-col items-center justify-center p-4">
              <div className="flex flex-col items-center space-y-8">
                <div 
                  className="w-[500px] h-[500px] rounded-lg shadow-xl overflow-hidden"
                  style={{
                    backgroundImage: 'url(/office_background.jpg)',
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                    backgroundRepeat: 'no-repeat'
                  }}
                >
                  <Avatar 
                    style={{ width: '100%', height: '100%' }}
                    isTalking={isAudioPlaying}
                  />
                </div>
                <div className="relative w-[800px] h-[120px] p-4 bg-white/5 border border-white/10 rounded-lg shadow-lg backdrop-blur-sm overflow-hidden animate-shimmer hide-scrollbar overflow-y-auto">
                  <p className="text-gray-300 text-center text-xl">{displayText}</p>
                </div>
                <div className="flex flex-col items-center space-y-4">
                  <MicButton 
                    isMuted={isMuted}
                    isListening={recordingState === RecordingState.LISTENING}
                    onClick={toggleMute} 
                  />
                  {connectionState !== WebSocketState.OPEN && (
                    <button
                      onClick={toggleConnection}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
                    >
                      Connect WebSocket
                    </button>
                  )}
                  <StartStopButton 
                    recordingState={isVoiceAgentRunning ? RecordingState.LISTENING : RecordingState.IDLE} 
                    onClick={() => {
                      if (isVoiceAgentRunning) {
                        stopVoiceAgent();
                      } else {
                        startVoiceAgent();
                      }
                    }} 
                  />
                </div>
              </div>
            </main>
        </div>

        <AudioDeviceSelector 
            devices={audioDevices}
            selectedDeviceId={selectedDeviceId}
            onDeviceSelect={handleDeviceSelect}
        />
    </div>
  );
};

export default App;
