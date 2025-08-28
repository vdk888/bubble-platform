"""
Security Service Interfaces - Sprint 2.5 Part D Implementation

Interface-First Design for enterprise security features including:
- Rate limiting with Redis backend
- Security audit trail logging  
- Input validation and sanitization
- Multi-tenant security enforcement

Following the Interface-First Design methodology from planning/0_dev.md
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum


class SecurityEventType(Enum):
    """Types of security events for audit logging"""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    API_ACCESS = "api_access"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_MODIFICATION = "data_modification"
    SECURITY_VIOLATION = "security_violation"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


@dataclass
class SecurityAlert:
    """Security alert data structure"""
    alert_id: str
    user_id: str
    event_type: SecurityEventType
    severity: str  # 'low', 'medium', 'high', 'critical'
    description: str
    details: Dict[str, Any]
    timestamp: datetime
    resolved: bool = False


@dataclass
class RateLimitInfo:
    """Rate limit information"""
    identifier: str
    endpoint: str
    current_count: int
    limit: int
    window_seconds: int
    reset_time: datetime
    blocked: bool


@dataclass
class ValidationResult:
    """Input validation result"""
    is_valid: bool
    errors: List[str]
    sanitized_data: Dict[str, Any]
    risk_score: float  # 0.0 (safe) to 1.0 (high risk)


class IRateLimiter(ABC):
    """
    Interface for rate limiting functionality.
    
    Provides enterprise-grade rate limiting with Redis backend
    supporting sliding window, fixed window, and token bucket algorithms.
    """
    
    @abstractmethod
    async def check_rate_limit(
        self, 
        identifier: str, 
        endpoint: str, 
        limit: int, 
        window_seconds: int
    ) -> bool:
        """
        Check if request is within rate limits.
        
        Args:
            identifier: User ID, IP address, or other identifier
            endpoint: API endpoint being accessed
            limit: Maximum requests allowed in window
            window_seconds: Time window in seconds
            
        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        pass
        
    @abstractmethod
    async def increment_counter(
        self, 
        identifier: str, 
        endpoint: str
    ) -> int:
        """
        Increment request counter and return current count.
        
        Args:
            identifier: User ID, IP address, or other identifier
            endpoint: API endpoint being accessed
            
        Returns:
            Current request count in the window
        """
        pass
    
    @abstractmethod
    async def get_rate_limit_info(
        self,
        identifier: str,
        endpoint: str
    ) -> RateLimitInfo:
        """
        Get detailed rate limit information for monitoring.
        
        Args:
            identifier: User ID, IP address, or other identifier
            endpoint: API endpoint being accessed
            
        Returns:
            Detailed rate limit information
        """
        pass
    
    @abstractmethod
    async def reset_rate_limit(
        self,
        identifier: str,
        endpoint: str
    ) -> bool:
        """
        Reset rate limit counter (admin function).
        
        Args:
            identifier: User ID, IP address, or other identifier
            endpoint: API endpoint being accessed
            
        Returns:
            True if reset successful
        """
        pass


class ISecurityAuditor(ABC):
    """
    Interface for security audit trail logging.
    
    Provides enterprise-grade audit logging with immutable trails,
    anomaly detection, and compliance reporting capabilities.
    """
    
    @abstractmethod
    async def log_security_event(
        self,
        user_id: str,
        event_type: SecurityEventType,
        endpoint: str,
        success: bool,
        details: Dict[str, Any] = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> str:
        """
        Log security-relevant event with immutable audit trail.
        
        Args:
            user_id: User performing the action
            event_type: Type of security event
            endpoint: API endpoint accessed
            success: Whether the action succeeded
            details: Additional event details
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Audit event ID for tracking
        """
        pass
    
    @abstractmethod
    async def detect_suspicious_activity(
        self,
        user_id: str,
        time_window_minutes: int = 10
    ) -> List[SecurityAlert]:
        """
        Detect patterns indicating potential security issues.
        
        Args:
            user_id: User to analyze
            time_window_minutes: Analysis time window
            
        Returns:
            List of security alerts if suspicious patterns detected
        """
        pass
    
    @abstractmethod
    async def get_audit_trail(
        self,
        user_id: str,
        start_time: datetime,
        end_time: datetime,
        event_types: List[SecurityEventType] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit trail for compliance reporting.
        
        Args:
            user_id: User to get trail for
            start_time: Start of time range
            end_time: End of time range
            event_types: Filter by event types
            
        Returns:
            List of audit events in chronological order
        """
        pass
    
    @abstractmethod
    async def create_security_alert(
        self,
        user_id: str,
        event_type: SecurityEventType,
        severity: str,
        description: str,
        details: Dict[str, Any] = None
    ) -> SecurityAlert:
        """
        Create high-priority security alert.
        
        Args:
            user_id: User involved in alert
            event_type: Type of security event
            severity: Alert severity level
            description: Human-readable description
            details: Additional alert details
            
        Returns:
            Created security alert
        """
        pass


class IInputValidator(ABC):
    """
    Interface for input validation and sanitization.
    
    Provides enterprise-grade input validation with SQL injection prevention,
    XSS protection, and business rule validation.
    """
    
    @abstractmethod
    async def validate_temporal_input(
        self,
        data: Dict[str, Any],
        schema: str = "temporal_universe_request"
    ) -> ValidationResult:
        """
        Validate temporal universe API inputs.
        
        Args:
            data: Input data to validate
            schema: Validation schema to use
            
        Returns:
            Validation result with sanitized data
        """
        pass
    
    @abstractmethod
    async def sanitize_user_input(
        self,
        input_data: Any,
        context: str = "general"
    ) -> Any:
        """
        Sanitize user input to prevent injection attacks.
        
        Args:
            input_data: Raw user input
            context: Context for sanitization rules
            
        Returns:
            Sanitized input safe for processing
        """
        pass
    
    @abstractmethod
    async def validate_business_rules(
        self,
        data: Dict[str, Any],
        operation: str,
        user_context: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate business logic constraints.
        
        Args:
            data: Data to validate
            operation: Business operation being performed
            user_context: User context for validation
            
        Returns:
            Validation result with business rule compliance
        """
        pass


class ITemporalCache(ABC):
    """
    Interface for temporal data caching.
    
    Provides enterprise-grade caching for temporal universe data
    with TTL management, invalidation strategies, and performance optimization.
    """
    
    @abstractmethod
    async def get_timeline(
        self,
        universe_id: str,
        start_date: str,
        end_date: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached timeline data.
        
        Args:
            universe_id: Universe identifier
            start_date: Timeline start date (ISO format)
            end_date: Timeline end date (ISO format)
            
        Returns:
            Cached timeline data if available
        """
        pass
        
    @abstractmethod
    async def set_timeline(
        self,
        universe_id: str,
        start_date: str,
        end_date: str,
        timeline_data: Dict[str, Any],
        ttl_seconds: int = 3600
    ) -> bool:
        """
        Cache timeline data with TTL.
        
        Args:
            universe_id: Universe identifier
            start_date: Timeline start date (ISO format)
            end_date: Timeline end date (ISO format)
            timeline_data: Timeline data to cache
            ttl_seconds: Time to live in seconds
            
        Returns:
            True if caching successful
        """
        pass
    
    @abstractmethod
    async def invalidate_universe_cache(
        self,
        universe_id: str
    ) -> bool:
        """
        Invalidate all cached data for a universe.
        
        Args:
            universe_id: Universe identifier
            
        Returns:
            True if invalidation successful
        """
        pass
    
    @abstractmethod
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.
        
        Returns:
            Cache statistics including hit rate, memory usage, etc.
        """
        pass


class IConcurrentProcessor(ABC):
    """
    Interface for memory-efficient concurrent processing.
    
    Provides enterprise-grade concurrent processing with memory limits,
    resource monitoring, and graceful degradation under load.
    """
    
    @abstractmethod
    async def process_with_memory_limit(
        self,
        tasks: List[Any],
        max_memory_mb: int = 500,
        batch_size: int = 10
    ) -> List[Any]:
        """
        Process tasks in batches with memory monitoring.
        
        Args:
            tasks: List of tasks to process
            max_memory_mb: Maximum memory usage in MB
            batch_size: Number of tasks per batch
            
        Returns:
            List of processed results
        """
        pass
    
    @abstractmethod
    async def get_system_resources(self) -> Dict[str, Any]:
        """
        Get current system resource usage.
        
        Returns:
            System resource information
        """
        pass
    
    @abstractmethod
    async def should_throttle(self) -> bool:
        """
        Check if processing should be throttled due to resource constraints.
        
        Returns:
            True if throttling recommended
        """
        pass


class ITurnoverOptimizer(ABC):
    """
    Interface for advanced turnover optimization.
    
    Provides enterprise-grade turnover optimization with mathematical
    precision, cost analysis, and scenario modeling.
    """
    
    @abstractmethod
    async def optimize_universe_changes(
        self,
        current_universe: List[str],
        candidate_universe: List[str],
        price_data: Dict[str, float],
        transaction_costs: Dict[str, float] = None,
        optimization_target: str = "minimize_turnover"
    ) -> Dict[str, Any]:
        """
        Optimize universe changes to meet business objectives.
        
        Args:
            current_universe: Current universe symbols
            candidate_universe: Proposed new universe symbols
            price_data: Current price data for symbols
            transaction_costs: Transaction cost per symbol
            optimization_target: Optimization objective
            
        Returns:
            Optimization results with recommended changes
        """
        pass
    
    @abstractmethod
    async def calculate_turnover_scenarios(
        self,
        current_universe: List[str],
        scenarios: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Calculate turnover for multiple scenarios.
        
        Args:
            current_universe: Current universe symbols
            scenarios: List of scenario definitions
            
        Returns:
            Turnover analysis for each scenario
        """
        pass
    
    @abstractmethod
    async def get_optimization_metrics(self) -> Dict[str, Any]:
        """
        Get turnover optimization performance metrics.
        
        Returns:
            Optimization performance statistics
        """
        pass