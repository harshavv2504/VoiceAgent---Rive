import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { RecordingState } from '../types';

interface UseAudioRecorderProps {
  selectedDeviceId: string;
  onAudioData?: (audioData: ArrayBuffer, sampleRate: number) => void;
}

export const useAudioRecorder = ({ selectedDeviceId, onAudioData }: UseAudioRecorderProps) => {
    const [recordingState, setRecordingState] = useState<RecordingState>(RecordingState.IDLE);
    const [isMuted, setIsMuted] = useState(false);
    const [audioLevel, setAudioLevel] = useState(0);
    const [bassLevel, setBassLevel] = useState(0);
    const [error, setError] = useState<string | null>(null);

    const audioContextRef = useRef<AudioContext | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const animationFrameIdRef = useRef<number | null>(null);
    const gainNodeRef = useRef<GainNode | null>(null);
    const scriptProcessorRef = useRef<ScriptProcessorNode | null>(null);
    
    const recordingStateRef = useRef(recordingState);
    useEffect(() => {
        recordingStateRef.current = recordingState;
    }, [recordingState]);

    const stopRecording = useCallback(() => {
        if (animationFrameIdRef.current) {
            cancelAnimationFrame(animationFrameIdRef.current);
            animationFrameIdRef.current = null;
        }
        if (scriptProcessorRef.current) {
            scriptProcessorRef.current.disconnect();
            scriptProcessorRef.current = null;
        }
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }
        if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
            audioContextRef.current.close().catch(console.error);
            audioContextRef.current = null;
        }
        gainNodeRef.current = null;
        setIsMuted(false);

        setAudioLevel(0);
        setBassLevel(0);
        setRecordingState(RecordingState.PROCESSING);
    }, []);

    const setProcessingState = useCallback((isProcessing: boolean) => {
        if (isProcessing) {
            if (recordingStateRef.current === RecordingState.IDLE || recordingStateRef.current === RecordingState.ERROR) {
                setRecordingState(RecordingState.PROCESSING);
            } else {
                console.warn(`Cannot programmatically enter processing state from ${recordingStateRef.current}. Must be IDLE or ERROR.`);
            }
        } else {
            if (recordingStateRef.current === RecordingState.PROCESSING) {
                setRecordingState(RecordingState.IDLE);
            }
        }
    }, []);

    const startRecording = useCallback(async () => {
        setError(null);
        setIsMuted(false);
        setRecordingState(RecordingState.REQUESTING_PERMISSION);
        try {
            const constraints: MediaStreamConstraints = {
                audio: selectedDeviceId ? { deviceId: { exact: selectedDeviceId } } : true
            };
            console.log('🎤 Requesting microphone permission with constraints:', constraints);
            const stream = await navigator.mediaDevices.getUserMedia(constraints);
            console.log('🎤 Microphone permission granted, stream received:', stream);
            streamRef.current = stream;

            const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
            audioContextRef.current = audioContext;
            const source = audioContext.createMediaStreamSource(stream);
            const gainNode = audioContext.createGain();
            gainNode.gain.value = 1;
            gainNodeRef.current = gainNode;
            const analyser = audioContext.createAnalyser();
            analyser.fftSize = 512;
            analyser.smoothingTimeConstant = 0.3;
            
            // Create script processor for audio data capture
            const scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
            scriptProcessorRef.current = scriptProcessor;
            
            scriptProcessor.onaudioprocess = (event) => {
                if (onAudioData && !isMuted) {
                    const inputBuffer = event.inputBuffer;
                    const inputData = inputBuffer.getChannelData(0);
                    
                    // Convert Float32Array to ArrayBuffer
                    const arrayBuffer = new ArrayBuffer(inputData.length * 2);
                    const dataView = new DataView(arrayBuffer);
                    for (let i = 0; i < inputData.length; i++) {
                        dataView.setInt16(i * 2, Math.max(-32768, Math.min(32767, inputData[i] * 32768)), true);
                    }
                    
                    onAudioData(arrayBuffer, audioContext.sampleRate);
                }
            };
            
            source.connect(gainNode);
            gainNode.connect(analyser);
            gainNode.connect(scriptProcessor);
            scriptProcessor.connect(audioContext.destination);

            const timeDomainDataArray = new Uint8Array(analyser.frequencyBinCount);
            const frequencyDataArray = new Uint8Array(analyser.frequencyBinCount);

            const updateAudioLevels = () => {
                analyser.getByteTimeDomainData(timeDomainDataArray);
                let sumSquares = 0.0;
                for (const amplitude of timeDomainDataArray) {
                    const value = (amplitude / 128.0) - 1.0;
                    sumSquares += value * value;
                }
                const rms = Math.sqrt(sumSquares / timeDomainDataArray.length);
                const level = Math.min(1, rms * 2.5);
                
                analyser.getByteFrequencyData(frequencyDataArray);
                const bassFrequencies = frequencyDataArray.slice(0, 32);
                const averageBass = bassFrequencies.reduce((sum, value) => sum + value, 0) / bassFrequencies.length;
                const normalizedBass = Math.min(1, (averageBass / 255.0) * 1.5);

                setAudioLevel(prevLevel => prevLevel * 0.7 + level * 0.3);
                setBassLevel(prevLevel => prevLevel * 0.7 + normalizedBass * 0.3);
                
                animationFrameIdRef.current = requestAnimationFrame(updateAudioLevels);
            };
            
            updateAudioLevels();
            setRecordingState(RecordingState.LISTENING);

        } catch (err) {
            console.error("Error accessing microphone:", err);
            if (err instanceof Error && err.name === 'NotAllowedError') {
                 setError("Microphone access denied. Please allow microphone access in your browser settings.");
            } else {
                setError("Could not access microphone. It may be in use by another application.");
            }
            setRecordingState(RecordingState.ERROR);
        }
    }, [selectedDeviceId, onAudioData, isMuted]);

    const toggleMute = useCallback(() => {
        if (recordingStateRef.current === RecordingState.LISTENING) {
            setIsMuted(prevMuted => {
                const newMuted = !prevMuted;
                if (gainNodeRef.current) {
                    gainNodeRef.current.gain.value = newMuted ? 0 : 1;
                }
                return newMuted;
            });
        }
    }, []);

    const audioRecorderApi = useMemo(() => ({
      recordingState,
      error,
      audioLevel,
      bassLevel,
      startRecording,
      stopRecording,
      setProcessingState,
      isMuted,
      toggleMute
    }), [recordingState, error, audioLevel, bassLevel, startRecording, stopRecording, setProcessingState, isMuted, toggleMute]);

    return audioRecorderApi;
};