from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./bakery.db"
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    session_cookie_name: str = "bakery_session"
    session_max_age: int = 86400  # 24 hours
    
    # Tax
    default_tax_rate: float = 0.10  # 10%
    
    # Application
    app_name: str = "Bakery POS"
    debug: bool = False
    
    class Config:
        env_file = ".env"


settings = Settings()

