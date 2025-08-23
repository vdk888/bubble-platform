from fastapi import APIRouter
import os
from datetime import datetime, timezone
from ...core.feature_flags import FeatureFlags, FeatureFlag

router = APIRouter()

@router.get("/")
async def get_feature_flags():
    """Get current feature flag status"""
    return {
        "features": FeatureFlags.get_all_flags(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": os.getenv("ENVIRONMENT", "development")
    }

@router.get("/enabled")
async def get_enabled_features():
    """Get list of enabled features only"""
    return {
        "enabled_features": FeatureFlags.get_enabled_flags(),
        "count": len(FeatureFlags.get_enabled_flags()),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.get("/info")
async def get_feature_info():
    """Get detailed feature flag information"""
    return FeatureFlags.get_flag_info()

@router.get("/{feature_name}")
async def check_feature(feature_name: str):
    """Check if a specific feature is enabled"""
    try:
        flag = FeatureFlag(feature_name)
        enabled = FeatureFlags.is_enabled(flag)
        return {
            "feature": feature_name,
            "enabled": enabled,
            "env_var": f"FEATURE_{feature_name.upper()}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except ValueError:
        return {
            "error": f"Unknown feature flag: {feature_name}",
            "available_flags": [flag.value for flag in FeatureFlag],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }