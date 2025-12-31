"""
Voice Agent Modules
Refactored components for the voice agent backend
"""
from .websocket_manager import ConnectionManager
from .voice_agent import VoiceAgent, set_manager_for_voice_agent
from .audio_handler import Speaker, get_audio_devices, set_manager_for_audio_playback
from .conversation_logger import ConversationLogger

__all__ = [
    'ConnectionManager',
    'VoiceAgent',
    'Speaker',
    'ConversationLogger',
    'get_audio_devices',
    'set_manager_for_voice_agent',
    'set_manager_for_audio_playback',
]
