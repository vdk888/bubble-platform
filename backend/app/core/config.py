from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator
import os

class Settings(BaseSettings):
    # Application
    app_name: str = "Bubble Platform"
    debug: bool = False
    environment: str = "development"
    secret_key: str
    
    # Database
    database_url: str
    database_test_url: Optional[str] = None
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # External APIs
    claude_api_key: str
    alpaca_api_key: str
    alpaca_secret_key: str
    yahoo_finance_api_key: Optional[str] = None
    
    # Authentication
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Business Logic
    rebalancing_threshold: float = 0.05
    max_single_allocation: float = 0.4
    paper_trading_enabled: bool = True
    
    # AI Agent
    max_conversation_history: int = 50
    ai_response_timeout: int = 30
    
    @field_validator('database_url')
    @classmethod
    def validate_database_url(cls, v):
        if 'sqlite' in v and os.getenv('ENVIRONMENT') == 'production':
            raise ValueError('SQLite not allowed in production')
        return v
    
    model_config = {"env_file": ".env", "case_sensitive": False, "extra": "ignore"}

settings = Settings()