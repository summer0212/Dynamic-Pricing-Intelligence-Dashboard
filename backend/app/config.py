from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    '''Application settings loaded from env'''
    
    DATABASE_URL : str

    # Auth
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440
    # AI
    GROQ_API_KEY: str
    # Temporal
    TEMPORAL_HOST: str = "localhost:7233"
    
    class Config:
        env_file = ".env"

settings = Settings()
