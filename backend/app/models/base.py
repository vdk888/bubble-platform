from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base, declared_attr
from datetime import datetime, timezone
import uuid

Base = declarative_base()

class BaseModel(Base):
    __abstract__ = True
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, 
                       default=lambda: datetime.now(timezone.utc), 
                       onupdate=lambda: datetime.now(timezone.utc), 
                       nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower() + 's'
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}