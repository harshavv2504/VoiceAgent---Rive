"""
Conversation Logger Module
Captures and saves voice agent conversations to JSON files
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ConversationLogger:
    """Logs voice agent conversations to JSON files"""
    
    def __init__(self, output_dir: str = "conversation_logs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.session_id: Optional[str] = None
        self.start_time: Optional[str] = None
        self.start_date: Optional[str] = None
        self.conversation: list = []
        self.log_file: Optional[Path] = None
        
    def start_session(self, request_id: str, timestamp: str):
        """Start a new conversation session"""
        self.session_id = request_id
        
        # Parse timestamp (format: HH:MM:SS.mmm)
        time_parts = timestamp.split(":")
        self.start_time = f"{time_parts[0]}:{time_parts[1]}"  # HH:MM
        
        # Get current date
        self.start_date = datetime.now().strftime("%Y-%m-%d")
        
        # Create log file name
        safe_session_id = request_id[:8]  # Use first 8 chars of session ID
        filename = f"conversation_{self.start_date}_{safe_session_id}.json"
        self.log_file = self.output_dir / filename
        
        # Initialize conversation list
        self.conversation = []
        
        logger.info(f"📝 Started logging conversation: {self.session_id[:8]}...")
        self._save_to_file()
        
    def add_message(self, role: str, content: str, timestamp: str):
        """Add a message to the conversation"""
        if not self.session_id:
            logger.warning("Cannot add message: No active session")
            return
            
        message = {
            "role": role,
            "content": content,
            "timestamp": timestamp
        }
        
        self.conversation.append(message)
        logger.debug(f"Added {role} message to conversation")
        
        # Save immediately to handle abrupt disconnections
        self._save_to_file()
        
    def _save_to_file(self):
        """Save conversation to JSON file"""
        if not self.log_file:
            return
            
        data = {
            "date": self.start_date,
            "time": self.start_time,
            "session_id": self.session_id,
            "conversation": self.conversation
        }
        
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved conversation to {self.log_file}")
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
            
    def end_session(self):
        """End the current conversation session"""
        if self.session_id:
            msg_count = len(self.conversation)
            logger.info(f"💾 Saved conversation ({msg_count} messages): {self.log_file.name}")
            self._save_to_file()  # Final save
            
        # Reset state
        self.session_id = None
        self.start_time = None
        self.start_date = None
        self.conversation = []
        self.log_file = None
        
    def get_conversation_data(self) -> Dict[str, Any]:
        """Get current conversation data"""
        return {
            "date": self.start_date,
            "time": self.start_time,
            "session_id": self.session_id,
            "conversation": self.conversation
        }
