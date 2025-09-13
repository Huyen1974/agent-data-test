from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding='utf-8')

    APP_NAME: str = "Agent Data API Skeleton"
    # Other configurations will be added here later

settings = Settings()
