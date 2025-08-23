import os
from enum import Enum
from typing import Dict, Any, List
from datetime import datetime, timezone

class FeatureFlag(str, Enum):
    """Available feature flags for the application"""
    ADVANCED_SCREENER = "advanced_screener"
    REAL_TIME_DATA = "real_time_data"
    MULTI_BROKER = "multi_broker"
    AI_AGENT_ADVANCED = "ai_agent_advanced"
    LIVE_PERFORMANCE = "live_performance"
    NOTIFICATIONS_MULTI_CHANNEL = "notifications_multi_channel"
    RISK_ANALYTICS = "risk_analytics"
    ALTERNATIVE_DATA = "alternative_data"
    PAPER_TRADING = "paper_trading"
    LIVE_TRADING = "live_trading"

class FeatureFlags:
    """Production-ready feature flag management"""
    
    @staticmethod
    def is_enabled(flag: FeatureFlag) -> bool:
        """Check if feature flag is enabled via environment variable"""
        env_key = f"FEATURE_{flag.value.upper()}"
        env_value = os.getenv(env_key, 'false').lower()
        return env_value in ('true', '1', 'yes', 'on', 'enabled')
    
    @staticmethod
    def get_all_flags() -> Dict[str, bool]:
        """Get status of all feature flags"""
        return {
            flag.value: FeatureFlags.is_enabled(flag) 
            for flag in FeatureFlag
        }
    
    @staticmethod
    def get_enabled_flags() -> List[str]:
        """Get list of enabled feature flags"""
        return [
            flag.value for flag in FeatureFlag 
            if FeatureFlags.is_enabled(flag)
        ]
    
    @staticmethod
    def get_flag_info() -> Dict[str, Any]:
        """Get detailed information about all feature flags"""
        return {
            "feature_flags": {
                flag.value: {
                    "enabled": FeatureFlags.is_enabled(flag),
                    "env_var": f"FEATURE_{flag.value.upper()}",
                    "description": FeatureFlags._get_flag_description(flag)
                }
                for flag in FeatureFlag
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_flags": len(FeatureFlag),
            "enabled_count": len(FeatureFlags.get_enabled_flags())
        }
    
    @staticmethod
    def _get_flag_description(flag: FeatureFlag) -> str:
        """Get description for feature flag"""
        descriptions = {
            FeatureFlag.ADVANCED_SCREENER: "Enhanced universe screening with multi-metric filtering",
            FeatureFlag.REAL_TIME_DATA: "Real-time market data feeds and streaming",
            FeatureFlag.MULTI_BROKER: "Support for multiple broker integrations",
            FeatureFlag.AI_AGENT_ADVANCED: "Advanced AI agent workflows and insights",
            FeatureFlag.LIVE_PERFORMANCE: "Real-time portfolio performance tracking",
            FeatureFlag.NOTIFICATIONS_MULTI_CHANNEL: "Multi-channel notification system",
            FeatureFlag.RISK_ANALYTICS: "Advanced risk analytics and VaR calculations",
            FeatureFlag.ALTERNATIVE_DATA: "Alternative data sources integration",
            FeatureFlag.PAPER_TRADING: "Paper trading simulation mode",
            FeatureFlag.LIVE_TRADING: "Live trading with real money"
        }
        return descriptions.get(flag, "Feature flag description not available")

# Convenience functions for common feature checks
def is_advanced_screener_enabled() -> bool:
    """Check if advanced screener is enabled"""
    return FeatureFlags.is_enabled(FeatureFlag.ADVANCED_SCREENER)

def is_real_time_data_enabled() -> bool:
    """Check if real-time data is enabled"""
    return FeatureFlags.is_enabled(FeatureFlag.REAL_TIME_DATA)

def is_ai_agent_advanced_enabled() -> bool:
    """Check if advanced AI agent features are enabled"""
    return FeatureFlags.is_enabled(FeatureFlag.AI_AGENT_ADVANCED)

def is_live_trading_enabled() -> bool:
    """Check if live trading is enabled"""
    return FeatureFlags.is_enabled(FeatureFlag.LIVE_TRADING)

def is_paper_trading_enabled() -> bool:
    """Check if paper trading is enabled"""
    return FeatureFlags.is_enabled(FeatureFlag.PAPER_TRADING)