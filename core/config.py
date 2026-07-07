from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):

    # Pydantic v2 Configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    gemini_default_model: str = "gemini-3.1-flash-lite"
    
    supabase_connection_string: str

    duckdb_file_path: str = "data/data.db"
    visualization_mode: str = "structured"  # 'structured' or 'code_gen'
    max_sql_retries: int = 3
    debug_mode: bool = False
    log_level: str = "INFO"


settings = Settings()

if __name__ == "__main__":
    print(settings.model_dump())