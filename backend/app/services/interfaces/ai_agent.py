"""
AI Agent Service Interface for Sprint 5 Implementation
Following Interface-First Design principles for AI-native investment platform

This interface defines the contract for AI agent services that enable natural language
interaction with all platform capabilities through Claude tool calling.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

from .base import BaseService, ServiceResult


class MessageRole(str, Enum):
    """AI conversation message roles"""
    USER = "user"
    ASSISTANT = "assistant" 
    SYSTEM = "system"
    TOOL = "tool"


class ToolCallStatus(str, Enum):
    """Status of AI tool call execution"""
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    REQUIRES_CONFIRMATION = "requires_confirmation"


class ActionPriority(str, Enum):
    """Priority levels for AI-suggested actions"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high" 
    CRITICAL = "critical"


class ChatMessage(BaseModel):
    """Individual chat message in AI conversation"""
    id: str
    conversation_id: str
    role: MessageRole
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tool_calls: Optional[List[Dict[str, Any]]] = None
    attachments: Optional[List[Dict[str, Any]]] = None


class ToolCall(BaseModel):
    """AI tool call execution details"""
    id: str
    name: str
    parameters: Dict[str, Any]
    status: ToolCallStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None
    requires_confirmation: bool = False
    confirmation_data: Optional[Dict[str, Any]] = None


class AIVisualization(BaseModel):
    """AI-generated visualizations and charts"""
    type: str  # "chart", "table", "metric_card", "comparison"
    title: str
    data: Dict[str, Any]
    config: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None


class AIResponse(BaseModel):
    """Complete AI agent response with all components"""
    message: str
    tool_calls: List[ToolCall] = Field(default_factory=list)
    visualizations: List[AIVisualization] = Field(default_factory=list)
    requires_confirmation: bool = False
    confirmation_data: Optional[Dict[str, Any]] = None
    suggested_actions: List[Dict[str, Any]] = Field(default_factory=list)
    context_updates: Dict[str, Any] = Field(default_factory=dict)


class UserContext(BaseModel):
    """User context for AI agent personalization"""
    user_id: str
    conversation_id: str
    session_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Platform State Context
    universes: List[Dict[str, Any]] = Field(default_factory=list)
    strategies: List[Dict[str, Any]] = Field(default_factory=list)
    portfolios: List[Dict[str, Any]] = Field(default_factory=list)
    recent_orders: List[Dict[str, Any]] = Field(default_factory=list)
    
    # User Preferences
    preferences: Dict[str, Any] = Field(default_factory=dict)
    risk_tolerance: Optional[str] = None
    investment_goals: List[str] = Field(default_factory=list)
    
    # Session Context
    current_workflow: Optional[str] = None
    active_operations: List[Dict[str, Any]] = Field(default_factory=list)


class AITool(BaseModel):
    """Definition of available AI tools"""
    name: str
    description: str
    parameters_schema: Dict[str, Any]
    requires_confirmation: bool = False
    category: str  # "universe", "strategy", "portfolio", "execution", "analysis"
    risk_level: str = "low"  # "low", "medium", "high", "critical"
    examples: List[Dict[str, Any]] = Field(default_factory=list)


class ConversationSummary(BaseModel):
    """Summary of conversation history for context management"""
    conversation_id: str
    user_id: str
    title: str
    summary: str
    key_decisions: List[str] = Field(default_factory=list)
    created_universes: List[str] = Field(default_factory=list)
    created_strategies: List[str] = Field(default_factory=list)
    executed_operations: List[str] = Field(default_factory=list)
    last_activity: datetime
    message_count: int


class IAIAgentService(BaseService):
    """
    AI Agent Service Interface for Natural Language Platform Control
    
    Enables users to interact with the entire Bubble Platform through conversational AI,
    supporting all platform operations via Claude tool calling architecture.
    """
    
    @abstractmethod
    async def process_message(
        self,
        message: str,
        user_context: UserContext,
        conversation_history: Optional[List[ChatMessage]] = None,
        max_history_length: int = 20
    ) -> ServiceResult[AIResponse]:
        """
        Process user message and generate AI response with tool calls
        
        Args:
            message: User's natural language input
            user_context: Current user state and preferences
            conversation_history: Recent conversation context
            max_history_length: Limit on conversation history to include
            
        Returns:
            ServiceResult containing AIResponse with message, tool calls, visualizations
        """
        pass
    
    @abstractmethod
    async def execute_tool_call(
        self,
        tool_call: ToolCall,
        user_context: UserContext
    ) -> ServiceResult[Dict[str, Any]]:
        """
        Execute a specific AI tool call
        
        Args:
            tool_call: Tool call details from AI agent
            user_context: User context for authorization and personalization
            
        Returns:
            ServiceResult with tool execution results
        """
        pass
    
    @abstractmethod
    async def get_available_tools(
        self,
        user_context: UserContext,
        category_filter: Optional[str] = None
    ) -> ServiceResult[List[AITool]]:
        """
        Get list of AI tools available to user
        
        Args:
            user_context: User context for permission-based filtering
            category_filter: Optional category to filter tools
            
        Returns:
            ServiceResult containing list of available AI tools
        """
        pass
    
    @abstractmethod
    async def handle_confirmation_request(
        self,
        tool_call_id: str,
        user_confirmed: bool,
        user_context: UserContext,
        confirmation_data: Optional[Dict[str, Any]] = None
    ) -> ServiceResult[AIResponse]:
        """
        Handle user confirmation for critical AI actions
        
        Args:
            tool_call_id: ID of tool call requiring confirmation
            user_confirmed: Whether user confirmed the action
            user_context: User context for authorization
            confirmation_data: Additional confirmation parameters
            
        Returns:
            ServiceResult with follow-up AI response
        """
        pass
    
    @abstractmethod
    async def generate_insights(
        self,
        user_context: UserContext,
        insight_type: str = "portfolio_analysis",
        parameters: Optional[Dict[str, Any]] = None
    ) -> ServiceResult[AIResponse]:
        """
        Generate proactive insights and recommendations
        
        Args:
            user_context: User context for personalized insights
            insight_type: Type of insight to generate
            parameters: Additional parameters for insight generation
            
        Returns:
            ServiceResult with AI-generated insights and recommendations
        """
        pass
    
    @abstractmethod
    async def create_conversation(
        self,
        user_id: str,
        title: Optional[str] = None,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> ServiceResult[str]:
        """
        Create new AI conversation session
        
        Args:
            user_id: User creating the conversation
            title: Optional conversation title
            initial_context: Initial context for conversation
            
        Returns:
            ServiceResult with conversation ID
        """
        pass
    
    @abstractmethod
    async def get_conversation_history(
        self,
        conversation_id: str,
        user_id: str,
        limit: int = 50,
        include_tool_calls: bool = True
    ) -> ServiceResult[List[ChatMessage]]:
        """
        Retrieve conversation history
        
        Args:
            conversation_id: ID of conversation to retrieve
            user_id: User ID for authorization
            limit: Maximum number of messages to retrieve
            include_tool_calls: Whether to include tool call details
            
        Returns:
            ServiceResult with conversation message history
        """
        pass
    
    @abstractmethod
    async def summarize_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> ServiceResult[ConversationSummary]:
        """
        Generate intelligent conversation summary
        
        Args:
            conversation_id: ID of conversation to summarize
            user_id: User ID for authorization
            
        Returns:
            ServiceResult with conversation summary
        """
        pass
    
    @abstractmethod
    async def suggest_next_actions(
        self,
        user_context: UserContext,
        current_operation: Optional[str] = None,
        priority_filter: Optional[ActionPriority] = None
    ) -> ServiceResult[List[Dict[str, Any]]]:
        """
        Suggest intelligent next actions based on user context
        
        Args:
            user_context: Current user state and context
            current_operation: Currently active operation
            priority_filter: Filter suggestions by priority level
            
        Returns:
            ServiceResult with list of suggested actions
        """
        pass


# AI Tool Categories for Sprint 5 Implementation
AI_TOOL_CATEGORIES = {
    "universe_management": [
        "create_universe",
        "add_assets_to_universe", 
        "validate_asset_symbols",
        "screen_assets_by_criteria",
        "analyze_universe_composition"
    ],
    "strategy_development": [
        "create_strategy",
        "configure_indicators",
        "run_backtest",
        "analyze_strategy_performance",
        "compare_strategies"
    ],
    "portfolio_management": [
        "create_portfolio",
        "calculate_risk_parity_allocation",
        "rebalance_portfolio",
        "analyze_portfolio_risk",
        "track_portfolio_performance"
    ],
    "market_analysis": [
        "fetch_market_data",
        "analyze_price_trends",
        "generate_technical_signals",
        "compare_asset_performance",
        "identify_market_opportunities"
    ],
    "execution_management": [
        "preview_orders",
        "submit_orders",
        "track_execution_status",
        "analyze_execution_costs",
        "manage_broker_connections"
    ],
    "risk_management": [
        "calculate_portfolio_var",
        "analyze_correlation_matrix",
        "stress_test_portfolio",
        "monitor_drawdown_limits",
        "generate_risk_reports"
    ]
}

# Critical Actions Requiring Confirmation
CRITICAL_ACTIONS = {
    "rebalance_portfolio",
    "submit_orders", 
    "modify_live_strategy",
    "delete_universe",
    "delete_strategy",
    "change_risk_limits",
    "modify_broker_settings"
}

# AI Response Templates for Consistent Formatting
AI_RESPONSE_TEMPLATES = {
    "confirmation_required": {
        "message_template": "I'd like to {action_description}. This will {impact_description}. Do you want me to proceed?",
        "confirmation_fields": ["estimated_cost", "affected_positions", "execution_timeline"]
    },
    "operation_success": {
        "message_template": "Successfully {action_completed}. {result_summary}",
        "suggested_actions": ["view_results", "create_related_operation", "setup_monitoring"]
    },
    "error_handling": {
        "message_template": "I encountered an issue while {action_attempted}: {error_description}. Let me suggest alternatives.",
        "suggested_actions": ["retry_operation", "modify_parameters", "contact_support"]
    }
}