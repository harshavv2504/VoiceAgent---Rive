"""
Audio Handler Module
Handles audio playback and processing for the voice agent
"""
import os
import sys
from contextlib import contextmanager
import pyaudio
import asyncio
import threading
import janus
import queue
import logging
import base64

@contextmanager
def suppress_stderr():
    """Suppress stderr to hide ALSA warnings"""
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    sys.stderr.flush()
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        yield
    finally:
        os.dup2(old_stderr, 2)
        os.close(old_stderr)

# Import common modules
try:
    from common.agent_templates import AGENT_AUDIO_SAMPLE_RATE
except ImportError:
    from backend.common.agent_templates import AGENT_AUDIO_SAMPLE_RATE

# Configure logger for this module
logger = logging.getLogger(__name__)


class Speaker:
    """Handles audio playback with support for both local and browser output"""
    
    def __init__(self, agent_audio_sample_rate=None, browser_output=False):
        self._queue = None
        self._stream = None
        self._thread = None
        self._stop = None
        self.agent_audio_sample_rate = (
            agent_audio_sample_rate if agent_audio_sample_rate else 16000
        )
        self.browser_output = browser_output
        self._loop = None

    def __enter__(self):
        """Initialize audio stream and playback thread"""
        # Only initialize PyAudio stream if not using browser output
        if not self.browser_output:
            with suppress_stderr():
                audio = pyaudio.PyAudio()
                self._stream = audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=self.agent_audio_sample_rate,
                    input=False,
                    output=True,
                )
        else:
            # For browser output, we don't need a local audio stream
            self._stream = None
            
        self._queue = janus.Queue()
        self._stop = threading.Event()
        self._loop = asyncio.get_event_loop()
        self._thread = threading.Thread(
            target=_play_audio,
            args=(self._queue, self._stream, self._stop, self.browser_output, self._loop),
            daemon=True,
        )
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Clean up audio resources"""
        self._stop.set()
        self._thread.join()
        if self._stream:
            self._stream.close()
        self._stream = None
        self._queue = None
        self._thread = None
        self._stop = None

    async def play(self, data):
        """Queue audio data for playback"""
        return await self._queue.async_q.put(data)

    def stop(self):
        """Stop playback and clear the queue"""
        if self._queue and self._queue.async_q:
            while not self._queue.async_q.empty():
                try:
                    self._queue.async_q.get_nowait()
                except janus.QueueEmpty:
                    break


def _play_audio(audio_out, stream, stop, browser_output=False, loop=None):
    """
    Audio playback thread function
    Handles both local audio output and browser streaming
    """
    # Import manager here to avoid circular imports
    try:
        from .websocket_manager import ConnectionManager
    except ImportError:
        try:
            from websocket_manager import ConnectionManager
        except ImportError:
            from backend.modules.websocket_manager import ConnectionManager
    
    # Get the global manager instance
    # This will be set by the main application
    manager = getattr(_play_audio, 'manager', None)
    
    seq = 0  # Sequence counter for browser audio chunks
    
    while not stop.is_set():
        try:
            data = audio_out.sync_q.get(True, 0.05)

            # If browser output is enabled, send audio to browser via WebSocket
            if browser_output and loop and manager:
                try:
                    audio_base64 = base64.b64encode(data).decode('utf-8')
                    
                    # Send audio data to browser clients with sample rate information
                    for websocket in manager.active_connections:
                        try:
                            asyncio.run_coroutine_threadsafe(
                                manager.send_json(
                                    {
                                        "type": "audio_output",
                                        "audio": audio_base64,
                                        "sampleRate": AGENT_AUDIO_SAMPLE_RATE,
                                        "seq": seq,
                                    },
                                    websocket
                                ),
                                loop
                            )
                        except Exception as e:
                            logger.error(f"Error sending audio to browser: {e}")
                    seq += 1
                except Exception as e:
                    logger.error(f"Error encoding audio for browser: {e}")

            elif not browser_output and stream is not None:
                # Local audio output
                stream.write(data)
                
        except queue.Empty:
            pass


def get_audio_devices():
    """Get list of available audio input devices"""
    try:
        with suppress_stderr():
            audio = pyaudio.PyAudio()
            info = audio.get_host_api_info_by_index(0)
            numdevices = info.get("deviceCount")

            input_devices = []
            for i in range(0, numdevices):
                device_info = audio.get_device_info_by_host_api_device_index(0, i)
                if device_info.get("maxInputChannels") > 0:
                    input_devices.append({"index": i, "name": device_info.get("name")})

            audio.terminate()
        return input_devices
    except Exception as e:
        logger.error(f"Error getting audio devices: {e}")
        return []


def set_manager_for_audio_playback(manager):
    """Set the ConnectionManager instance for audio playback"""
    _play_audio.manager = manager
