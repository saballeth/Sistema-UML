from pydantic import BaseSettings

class Settings(BaseSettings):
    api_url: str = "http://localhost:8000/api/v1/chat"
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()