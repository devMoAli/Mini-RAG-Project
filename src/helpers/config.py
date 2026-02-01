from pydantic_settings import BaseSettings, SettingsConfigDict
import os

# 1. Logic: Go up one level from 'src/helpers' to find '.env' in 'src'
# current_file: src/helpers/config.py -> dirname: src/helpers -> dirname: src
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE_PATH = os.path.join(BASE_DIR, ".env")


class Settings(BaseSettings):
    # Required Fields (Must be in .env)
    APP_NAME: str
    APP_VERSION: str

    FILE_ALLOWED_TYPES: list
    FILE_MAX_SIZE: int
    FILE_DEFAULT_CHUNK_SIZE: int

    MONGODB_URI: str
    MONGODB_DB_NAME: str

    GENERATION_BACKEND: str
    EMBEDDING_BACKEND: str
    VECTORDB_BACKEND: str 
    VECTOR_DB_PATH: str 
    VECTOR_DB_DISTANCE_METHOD: str 

    PRIMARY_LANG: str = "en"
    DEFAULT_LANG: str = "en"

    # Optional Fields (Default to None if missing)
    OPENAI_API_KEY: str = None
    OPENAI_API_URL: str = None
    COHERE_API_KEY: str = None

    GENERATION_MODEL_ID: str = None
    EMBEDDING_MODEL_ID: str = None
    EMBEDDING_MODEL_SIZE: int = None

    INPUT_DEFAULT_MAX_CHARACTERS: int = None
    GENERATION_DEFAULT_MAX_TOKENS: int = None
    GENERATION_DEFAULT_TEMPERATURE: float = None

    # CRITICAL: This must be INSIDE the class
    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH, extra="ignore")


def get_settings() -> Settings:
    # Casual debug for you
    print(f"DEBUG: Looking for .env at: {ENV_FILE_PATH}")
    print(f"DEBUG: .env exists? {os.path.exists(ENV_FILE_PATH)}")
    return Settings()
