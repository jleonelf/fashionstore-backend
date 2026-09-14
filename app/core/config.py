import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "FashionStore API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # PostgreSQL config
    DATABASE_URL: str | None = os.getenv("DATABASE_URL", None)
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "fashionstore_db")

    # JWT Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "fashionstore_super_secret_jwt_key_si2_2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 día

    # Job de expiración CU24 (scheduler apagado por defecto; activar en producción)
    EXPIRACION_JOB_ACTIVO: bool = os.getenv("EXPIRACION_JOB_ACTIVO", "false").lower() == "true"
    EXPIRACION_JOB_MINUTOS: int = int(os.getenv("EXPIRACION_JOB_MINUTOS", "10"))

    @property
    def sync_database_url(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            elif url.startswith("postgresql+asyncpg://"):
                url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
            return url
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            # Separar base y query string para descartar parametros incompatibles con asyncpg (channel_binding, sslmode, etc.)
            base_url = url.split("?")[0]
            if base_url.startswith("postgres://"):
                base_url = base_url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif base_url.startswith("postgresql://"):
                base_url = base_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            
            # Si la URL usa SSL o es de Neon / AWS, agregar unicamente ?ssl=require
            if "ssl" in url.lower() or "neon.tech" in url.lower():
                return f"{base_url}?ssl=require"
            return base_url
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        case_sensitive = True
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")

settings = Settings()
