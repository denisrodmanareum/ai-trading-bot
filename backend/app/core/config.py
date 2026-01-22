"""
Application Configuration
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union


class Settings(BaseSettings):
    """Application settings"""
    
    # ⚠️ 여기에 바이낸스 API 키를 직접 입력하세요!
    BINANCE_API_KEY: str = "eOMptqOdKQbWm7IdL9ueqIRxm2DXFomdTZ4kiSKT9CT6TQnPev3sZZFpy8OixiXU"
    BINANCE_API_SECRET: str = "f73VOu6R4tEsLZD8KFgQRx6IcqQUM2vXFDp7hex2Yh0YtbUIKkGjdZKGNMQWPFZO"
    BINANCE_TESTNET: bool = True
    
    # Trading
    INITIAL_BALANCE: float = 10000.0
    LEVERAGE: int = 5
    
    # Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    
    # AI
    AI_MODEL_PATH: str = "data/models/"
    AI_LEARNING_RATE: float = 0.0003
    AI_GAMMA: float = 0.99
    AI_BATCH_SIZE: int = 64
    AI_UPDATE_EPOCHS: int = 10
    
    # CORS
    ALLOWED_ORIGINS: Union[str, List[str]] = ["*"]
    
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            if v.strip() == "*":
                return ["*"]
            return [x.strip() for x in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
