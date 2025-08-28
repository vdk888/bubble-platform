"""
Input Validator Implementation - Sprint 2.5 Part D

Enterprise-grade input validation and sanitization with XSS protection,
SQL injection prevention, and business rule validation.

Following Interface-First Design methodology from planning/0_dev.md
"""
import re
import html
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, date
import bleach
from urllib.parse import urlparse, parse_qs

from ..interfaces.security import IInputValidator, ValidationResult


class EnterpriseInputValidator(IInputValidator):
    """
    Enterprise-grade input validator with comprehensive security features.
    
    Features:
    - XSS protection via HTML sanitization
    - SQL injection prevention
    - Business rule validation
    - Temporal data validation
    - Custom sanitization rules per context
    """
    
    def __init__(self):
        """Initialize input validator with security configurations."""
        
        # XSS protection configuration
        self.allowed_tags = [
            # Minimal safe HTML tags
            'b', 'i', 'strong', 'em', 'u', 's', 'sup', 'sub',
            'br', 'p', 'span'
        ]
        
        self.allowed_attributes = {
            '*': ['class', 'id'],
            'span': ['style']  # Limited style attributes
        }
        
        # SQL injection patterns to detect
        self.sql_injection_patterns = [
            r'union\s+select',
            r'drop\s+table',
            r'delete\s+from',
            r'insert\s+into',
            r'update\s+set',
            r'alter\s+table',
            r'create\s+table',
            r'truncate\s+table',
            r'exec\s*\(',
            r'execute\s*\(',
            r'sp_executesql',
            r'xp_cmdshell',
            r'--|#|/\*|\*/',  # SQL comments
            r'\';\s*(drop|delete|update|insert|alter|create|truncate)',
            r'1=1|1\s*=\s*1',
            r'or\s+1\s*=\s*1',
            r'and\s+1\s*=\s*1'
        ]
        
        # Temporal data validation schemas
        self.temporal_schemas = {
            "temporal_universe_request": {
                "universe_id": {"type": "uuid", "required": True},
                "start_date": {"type": "date", "required": False},
                "end_date": {"type": "date", "required": False},
                "frequency": {"type": "enum", "values": ["daily", "weekly", "monthly", "quarterly"], "required": False}
            },
            "backfill_request": {
                "start_date": {"type": "date", "required": True},
                "end_date": {"type": "date", "required": True},
                "frequency": {"type": "enum", "values": ["daily", "weekly", "monthly", "quarterly"], "required": False}
            },
            "snapshot_request": {
                "snapshot_date": {"type": "date", "required": False},
                "screening_criteria": {"type": "object", "required": False},
                "force_recreation": {"type": "boolean", "required": False}
            }
        }
    
    def _sanitize_html(self, text: str) -> str:
        """
        Sanitize HTML content to prevent XSS attacks.
        
        Args:
            text: Raw HTML text
            
        Returns:
            Sanitized HTML safe for display
        """
        if not isinstance(text, str):
            return str(text)
        
        # Use bleach library for robust HTML sanitization
        sanitized = bleach.clean(
            text,
            tags=self.allowed_tags,
            attributes=self.allowed_attributes,
            strip=True,  # Remove disallowed tags completely
            strip_comments=True  # Remove HTML comments
        )
        
        # Additional escape for any remaining special characters
        return html.escape(sanitized, quote=True)
    
    def _detect_sql_injection(self, text: str) -> bool:
        """
        Detect potential SQL injection patterns.
        
        Args:
            text: Input text to analyze
            
        Returns:
            True if potential SQL injection detected
        """
        if not isinstance(text, str):
            return False
        
        # Normalize text for analysis
        normalized = text.lower().strip()
        
        # Check against known SQL injection patterns
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, normalized, re.IGNORECASE):
                return True
        
        return False
    
    def _validate_uuid(self, value: str) -> bool:
        """Validate UUID format."""
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        return bool(uuid_pattern.match(value))
    
    def _validate_date(self, value: str) -> bool:
        """Validate ISO date format."""
        try:
            datetime.fromisoformat(value.replace('Z', '+00:00'))
            return True
        except (ValueError, AttributeError):
            return False
    
    def _calculate_risk_score(self, data: Dict[str, Any], errors: List[str]) -> float:
        """
        Calculate risk score based on validation results.
        
        Args:
            data: Input data
            errors: Validation errors
            
        Returns:
            Risk score from 0.0 (safe) to 1.0 (high risk)
        """
        risk_factors = 0
        total_factors = 10
        
        # Check for SQL injection patterns
        for key, value in data.items():
            if isinstance(value, str) and self._detect_sql_injection(value):
                risk_factors += 3  # High risk
                break
        
        # Check for script tags or suspicious patterns
        for key, value in data.items():
            if isinstance(value, str):
                if '<script' in value.lower() or 'javascript:' in value.lower():
                    risk_factors += 2
                if 'eval(' in value.lower() or 'document.' in value.lower():
                    risk_factors += 1
        
        # Factor in validation errors
        if errors:
            risk_factors += min(len(errors), 3)
        
        # Check for unusual data patterns
        if any(isinstance(v, str) and len(v) > 10000 for v in data.values()):
            risk_factors += 1  # Very long inputs
        
        return min(risk_factors / total_factors, 1.0)
    
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
        errors = []
        sanitized_data = {}
        
        if schema not in self.temporal_schemas:
            errors.append(f"Unknown validation schema: {schema}")
            return ValidationResult(
                is_valid=False,
                errors=errors,
                sanitized_data=data,
                risk_score=1.0
            )
        
        schema_def = self.temporal_schemas[schema]
        
        # Validate each field according to schema
        for field_name, field_def in schema_def.items():
            value = data.get(field_name)
            
            # Check required fields
            if field_def.get("required", False) and value is None:
                errors.append(f"Required field '{field_name}' is missing")
                continue
            
            # Skip validation for optional fields that are None
            if value is None and not field_def.get("required", False):
                sanitized_data[field_name] = None
                continue
            
            # Type-specific validation
            field_type = field_def.get("type")
            
            if field_type == "uuid":
                if not self._validate_uuid(str(value)):
                    errors.append(f"Field '{field_name}' must be a valid UUID")
                else:
                    sanitized_data[field_name] = str(value)
            
            elif field_type == "date":
                if not self._validate_date(str(value)):
                    errors.append(f"Field '{field_name}' must be a valid ISO date")
                else:
                    sanitized_data[field_name] = str(value)
            
            elif field_type == "enum":
                allowed_values = field_def.get("values", [])
                if value not in allowed_values:
                    errors.append(f"Field '{field_name}' must be one of: {', '.join(allowed_values)}")
                else:
                    sanitized_data[field_name] = value
            
            elif field_type == "boolean":
                if not isinstance(value, bool):
                    # Try to convert string boolean
                    if str(value).lower() in ['true', '1', 'yes']:
                        sanitized_data[field_name] = True
                    elif str(value).lower() in ['false', '0', 'no']:
                        sanitized_data[field_name] = False
                    else:
                        errors.append(f"Field '{field_name}' must be a boolean value")
                else:
                    sanitized_data[field_name] = value
            
            elif field_type == "object":
                # Validate JSON objects
                if isinstance(value, dict):
                    # Recursively sanitize object values
                    sanitized_obj = {}
                    for k, v in value.items():
                        if isinstance(v, str):
                            sanitized_obj[k] = self._sanitize_html(v)
                        else:
                            sanitized_obj[k] = v
                    sanitized_data[field_name] = sanitized_obj
                else:
                    errors.append(f"Field '{field_name}' must be a valid object")
            
            else:
                # Default string handling with sanitization
                sanitized_value = self._sanitize_html(str(value))
                
                # Check for SQL injection
                if self._detect_sql_injection(str(value)):
                    errors.append(f"Field '{field_name}' contains potentially dangerous content")
                else:
                    sanitized_data[field_name] = sanitized_value
        
        # Include any additional fields with sanitization
        for key, value in data.items():
            if key not in sanitized_data:
                if isinstance(value, str):
                    sanitized_data[key] = self._sanitize_html(value)
                else:
                    sanitized_data[key] = value
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(data, errors)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_data=sanitized_data,
            risk_score=risk_score
        )
    
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
        if isinstance(input_data, str):
            # Apply context-specific sanitization
            if context == "html":
                return self._sanitize_html(input_data)
            elif context == "sql":
                # Escape single quotes and other SQL metacharacters
                return input_data.replace("'", "''").replace(";", "\\;")
            elif context == "json":
                try:
                    # Validate JSON and re-serialize
                    parsed = json.loads(input_data)
                    return json.dumps(parsed)
                except json.JSONDecodeError:
                    return html.escape(input_data)
            else:
                # General sanitization
                return self._sanitize_html(input_data)
        
        elif isinstance(input_data, dict):
            # Recursively sanitize dictionary values
            sanitized = {}
            for key, value in input_data.items():
                sanitized_key = self._sanitize_html(str(key))
                sanitized_value = await self.sanitize_user_input(value, context)
                sanitized[sanitized_key] = sanitized_value
            return sanitized
        
        elif isinstance(input_data, list):
            # Sanitize list items
            return [await self.sanitize_user_input(item, context) for item in input_data]
        
        else:
            # For other data types, return as-is (numbers, booleans, None)
            return input_data
    
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
        errors = []
        sanitized_data = data.copy()
        
        # Operation-specific business rules
        if operation == "backfill_universe":
            # Validate date range
            start_date_str = data.get("start_date")
            end_date_str = data.get("end_date")
            
            if start_date_str and end_date_str:
                try:
                    start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                    end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                    
                    if start_date >= end_date:
                        errors.append("Start date must be before end date")
                    
                    # Limit backfill range to prevent resource exhaustion
                    max_days = 365 * 5  # 5 years maximum
                    if (end_date - start_date).days > max_days:
                        errors.append(f"Backfill range cannot exceed {max_days} days")
                    
                    # Don't allow future dates
                    now = datetime.now(start_date.tzinfo)
                    if end_date > now:
                        errors.append("End date cannot be in the future")
                        
                except ValueError:
                    errors.append("Invalid date format")
        
        elif operation == "create_snapshot":
            # Validate snapshot date
            snapshot_date_str = data.get("snapshot_date")
            if snapshot_date_str:
                try:
                    snapshot_date = datetime.fromisoformat(snapshot_date_str.replace('Z', '+00:00'))
                    
                    # Don't allow future snapshots
                    now = datetime.now(snapshot_date.tzinfo)
                    if snapshot_date > now:
                        errors.append("Snapshot date cannot be in the future")
                        
                except ValueError:
                    errors.append("Invalid snapshot date format")
        
        elif operation == "universe_timeline":
            # Validate timeline request parameters
            start_date = data.get("start_date")
            end_date = data.get("end_date")
            
            if start_date and end_date:
                try:
                    start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    
                    # Limit timeline range
                    max_timeline_days = 365 * 2  # 2 years maximum
                    if (end - start).days > max_timeline_days:
                        errors.append(f"Timeline range cannot exceed {max_timeline_days} days")
                        
                except ValueError:
                    errors.append("Invalid date format in timeline request")
        
        # User context validations
        user_tier = user_context.get("subscription_tier", "free")
        
        if user_tier == "free":
            # Free tier limitations
            if operation == "backfill_universe":
                errors.append("Backfill operation requires Pro subscription")
            
            if operation == "universe_timeline":
                # Limit timeline range for free users
                start_date = data.get("start_date")
                end_date = data.get("end_date")
                if start_date and end_date:
                    try:
                        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                        
                        if (end - start).days > 90:  # 3 months max for free
                            errors.append("Free tier limited to 90 days of timeline data")
                    except ValueError:
                        pass  # Date validation already handled above
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(data, errors)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_data=sanitized_data,
            risk_score=risk_score
        )