from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    AZURE_OCR_ENDPOINT: str
    AZURE_OCR_KEY: str
    ALLOWED_ORIGINS: str = "http://localhost:3000,https://localhost:3000"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: set = {"png", "jpg", "jpeg", "gif", "bmp", "tiff", "webp"}
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings():
    return Settings()