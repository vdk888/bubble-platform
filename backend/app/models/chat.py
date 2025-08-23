from sqlalchemy import Column, String, Text, ForeignKey, JSON, DateTime, Enum as SQLEnum, Boolean, Integer
from sqlalchemy.orm import relationship
from enum import Enum
from datetime import datetime, timezone
from .base import BaseModel

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ConversationStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"

class Conversation(BaseModel):
    __tablename__ = "conversations"
    
    title = Column(String(200))  # Conversation title (optional)
    status = Column(SQLEnum(ConversationStatus), default=ConversationStatus.ACTIVE)
    
    # Context and metadata
    context_summary = Column(Text)  # AI-generated summary of conversation
    user_preferences = Column(JSON)  # User preferences learned during conversation
    
    # Timestamps
    last_message_at = Column(DateTime(timezone=True))
    
    # User relationship
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="conversations")
    
    # Messages relationship
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="ChatMessage.created_at")

class ChatMessage(BaseModel):
    __tablename__ = "chat_messages"
    
    role = Column(SQLEnum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    
    # Tool calling data
    tool_calls = Column(JSON)  # Tool calls made in this message
    tool_results = Column(JSON)  # Results from tool calls
    
    # Message metadata
    message_metadata = Column(JSON)  # Additional message data (charts, tables, etc.)
    confirmation_required = Column(Boolean, default=False)
    confirmation_data = Column(JSON)
    user_confirmed = Column(Boolean)
    
    # Processing info
    processing_time_ms = Column(Integer)  # Time taken to process
    error_message = Column(Text)  # Error if message processing failed
    
    # Conversation relationship
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    conversation = relationship("Conversation", back_populates="messages")