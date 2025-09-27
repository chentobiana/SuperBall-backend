import os
from dotenv import load_dotenv

# טוען את משתני הסביבה מקובץ .env
load_dotenv()


class Settings:
    # MongoDB Configuration
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "superball_game")
    
    # JWT Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Collections Names
    USERS_COLLECTION: str = "users"
    GAME_SESSIONS_COLLECTION: str = "game_sessions"

    # Game Rules
    TOTAL_ROUNDS: int = int(os.getenv("TOTAL_ROUNDS", "5"))
    TURNS_PER_ROUND: int = int(os.getenv("TURNS_PER_ROUND", "2"))
    TURN_SECONDS: int = int(os.getenv("TURN_SECONDS", "30"))


settings = Settings()
