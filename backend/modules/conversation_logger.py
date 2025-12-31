"""
Conversation Logger Module
Captures and saves voice agent conversations to MongoDB
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from common.database import db

logger = logging.getLogger(__name__)


class ConversationLogger:
    """Logs voice agent conversations to MongoDB"""
    
    def __init__(self, output_dir: str = "conversation_logs"):
        # output_dir parameter kept for backward compatibility but not used
        self.session_id: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.conversation: list = []
        
    def start_session(self, request_id: str, timestamp: str):
        """Start a new conversation session"""
        self.session_id = request_id
        self.start_time = datetime.now()
        self.conversation = []
        
        logger.info(f"📝 Started logging conversation: {self.session_id[:8]}...")
        
    async def add_message(self, role: str, content: str, timestamp: str):
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
        
        # Save immediately to MongoDB to handle abrupt disconnections
        await self._save_to_db()
        
    async def _save_to_db(self):
        """Save conversation to MongoDB"""
        if not self.session_id or not db:
            return
            
        try:
            duration = (datetime.now() - self.start_time).total_seconds() if self.start_time else None
            await db.save_conversation(
                session_id=self.session_id,
                messages=self.conversation,
                timestamp=self.start_time.isoformat() if self.start_time else datetime.now().isoformat(),
                duration=duration
            )
            logger.debug(f"Saved conversation to MongoDB: {self.session_id[:8]}")
        except Exception as e:
            logger.error(f"Error saving conversation to MongoDB: {e}")
            
    async def end_session(self):
        """End the current conversation session"""
        if self.session_id:
            msg_count = len(self.conversation)
            await self._save_to_db()  # Final save to MongoDB
            logger.info(f"💾 Saved conversation ({msg_count} messages) to MongoDB: {self.session_id[:8]}")
            
        # Reset state
        self.session_id = None
        self.start_time = None
        self.conversation = []
        
    def get_conversation_data(self) -> Dict[str, Any]:
        """Get current conversation data"""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "messages": self.conversation,
            "message_count": len(self.conversation)
        }
