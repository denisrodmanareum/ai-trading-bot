"""
Exchange Client Factory
"""
from typing import Union, Optional
from loguru import logger
from app.core.config import settings
from trading.binance_client import BinanceClient
from trading.base_client import BaseExchangeClient

class ExchangeFactory:
    """Factory to create and manage exchange clients"""
    
    _instance: Optional[BaseExchangeClient] = None
    _active_exchange: str = ""

    @classmethod
    async def get_client(cls) -> BaseExchangeClient:
        """Get the active exchange client instance"""
        target_exchange = settings.ACTIVE_EXCHANGE.upper()
        
        # If client exists and exchange type matches, return it
        if cls._instance and cls._active_exchange == target_exchange:
            return cls._instance
            
        # Otherwise, create new instance
        logger.info(f"🔄 Switching Exchange Client to: {target_exchange}")
        
        if target_exchange == "BINANCE":
            cls._instance = BinanceClient()
        elif target_exchange == "BYBIT":
            # Lazy import to avoid issues if Bybit dependencies aren't met
            try:
                from trading.bybit_client import BybitClient
                cls._instance = BybitClient()
            except ImportError as e:
                logger.error(f"Failed to load BybitClient: {e}")
                cls._instance = BinanceClient() # Fallback
        else:
            logger.warning(f"Unknown exchange: {target_exchange}. Defaulting to BINANCE.")
            cls._instance = BinanceClient()
            
        await cls._instance.initialize()
        cls._active_exchange = target_exchange
        return cls._instance

    @classmethod
    async def reload(cls):
        """Force reload client (e.g. after API key update)"""
        if cls._instance:
            await cls._instance.close()
            cls._instance = None
        return await cls.get_client()
