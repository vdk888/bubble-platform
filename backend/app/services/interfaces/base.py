from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic
from datetime import datetime
from pydantic import BaseModel

T = TypeVar('T')

class ServiceResult(BaseModel, Generic[T]):
    """Standard service response wrapper for AI-friendly responses"""
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    message: str = ""
    metadata: Dict[str, Any] = {}
    next_actions: List[str] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ServiceResult to dictionary for Pydantic V2 compatibility"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "message": self.message,
            "metadata": self.metadata,
            "next_actions": self.next_actions
        }

class BaseService(ABC):
    """Base service interface with common patterns"""
    
    @abstractmethod
    async def health_check(self) -> ServiceResult[Dict[str, Any]]:
        """Service health status"""
        pass