"""
Settings configuration for the API service
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Knowledge Tree API"
    PROJECT_ID: str = os.getenv("GOOGLE_CLOUD_PROJECT", "github-chatgpt-ggcloud")
    
    class Config:
        env_file = ".env"


settings = Settings()
