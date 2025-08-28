"""
Security Audit Models - Sprint 2.5 Part D Implementation

Database models for enterprise security audit trail and alerting.
Supports immutable audit logging with cryptographic integrity.

Following security-by-design principles from planning/7_risk_system.md
"""
from sqlalchemy import Column, String, Boolean, DateTime, JSON, Text, Index
from sqlalchemy.sql import func
from datetime import datetime, timezone
from typing import Dict, Any

from .base import BaseModel


class SecurityAuditLog(BaseModel):
    """
    Immutable security audit log entries.
    
    Records all security-relevant events with cryptographic integrity verification.
    Supports compliance reporting and forensic analysis.
    """
    __tablename__ = "security_audit_logs"
    
    # Core event information
    user_id = Column(String(36), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # SecurityEventType enum values
    endpoint = Column(String(255), nullable=True, index=True)
    success = Column(Boolean, nullable=False, default=False, index=True)
    
    # Request context
    ip_address = Column(String(45), nullable=True, index=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    
    # Event details (flexible JSON storage)
    details = Column(JSON, nullable=True)
    
    # Integrity verification
    integrity_hash = Column(String(64), nullable=False)  # SHA-256 hash
    
    # Immutable timestamp (cannot be updated)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure created_at is set and immutable
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit log to dictionary for JSON serialization."""
        return {
            "event_id": self.id,
            "user_id": self.user_id,
            "event_type": self.event_type,
            "endpoint": self.endpoint,
            "success": self.success,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "details": self.details,
            "integrity_hash": self.integrity_hash,
            "timestamp": self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f"<SecurityAuditLog(id='{self.id}', user_id='{self.user_id}', event_type='{self.event_type}', success={self.success})>"


class SecurityAlertModel(BaseModel):
    """
    Security alerts for suspicious activity detection.
    
    Stores high-priority security alerts requiring investigation or response.
    Supports alert management and incident response workflows.
    """
    __tablename__ = "security_alerts"
    
    # Alert information
    user_id = Column(String(36), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # SecurityEventType enum values
    severity = Column(String(20), nullable=False, index=True)  # low, medium, high, critical
    description = Column(Text, nullable=False)
    
    # Alert details (flexible JSON storage)
    details = Column(JSON, nullable=True)
    
    # Alert lifecycle
    resolved = Column(Boolean, nullable=False, default=False, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(36), nullable=True)  # User ID who resolved the alert
    resolution_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    def resolve(self, resolved_by: str, notes: str = None):
        """
        Mark alert as resolved.
        
        Args:
            resolved_by: User ID who resolved the alert
            notes: Optional resolution notes
        """
        self.resolved = True
        self.resolved_at = datetime.now(timezone.utc)
        self.resolved_by = resolved_by
        self.resolution_notes = notes
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert security alert to dictionary for JSON serialization."""
        return {
            "alert_id": self.id,
            "user_id": self.user_id,
            "event_type": self.event_type,
            "severity": self.severity,
            "description": self.description,
            "details": self.details,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "resolution_notes": self.resolution_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f"<SecurityAlert(id='{self.id}', user_id='{self.user_id}', severity='{self.severity}', resolved={self.resolved})>"


# Database indexes for performance optimization
Index('idx_security_audit_user_time', SecurityAuditLog.user_id, SecurityAuditLog.created_at)
Index('idx_security_audit_event_time', SecurityAuditLog.event_type, SecurityAuditLog.created_at)
Index('idx_security_audit_success_time', SecurityAuditLog.success, SecurityAuditLog.created_at)
Index('idx_security_audit_ip_time', SecurityAuditLog.ip_address, SecurityAuditLog.created_at)

Index('idx_security_alerts_user_severity', SecurityAlertModel.user_id, SecurityAlertModel.severity)
Index('idx_security_alerts_resolved_time', SecurityAlertModel.resolved, SecurityAlertModel.created_at)
Index('idx_security_alerts_event_severity', SecurityAlertModel.event_type, SecurityAlertModel.severity)