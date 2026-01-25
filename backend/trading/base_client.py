"""
Base Exchange Client Interface
"""
from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, List, Optional, Union

class BaseExchangeClient(ABC):
    """Abstract Base Class for Exchange Clients"""
    
    @abstractmethod
    async def initialize(self):
        """Initialize client"""
        pass
    
    @abstractmethod
    async def close(self):
        """Close connection"""
        pass
    
    @abstractmethod
    async def get_account_info(self) -> Dict:
        """Get account info"""
        pass
    
    @abstractmethod
    async def get_current_price(self, symbol: str) -> float:
        """Get current price"""
        pass
    
    @abstractmethod
    async def get_klines(self, symbol: str, interval: str, limit: int) -> pd.DataFrame:
        """Get klines/candles"""
        pass
    
    @abstractmethod
    async def get_position(self, symbol: str) -> Dict:
        """Get position information"""
        pass
    
    @abstractmethod
    async def get_all_positions(self) -> List[Dict]:
        """Get all active positions"""
        pass
    
    @abstractmethod
    async def place_market_order(self, symbol: str, side: str, quantity: float, reduce_only: bool = False) -> Dict:
        """Place market order"""
        pass
    
    @abstractmethod
    async def place_bracket_orders(
        self,
        symbol: str,
        position_side: str,
        quantity: float,
        stop_loss_price: Optional[float],
        take_profit_price: Optional[float]
    ) -> Dict:
        """Place SL/TP bracket orders"""
        pass

    @abstractmethod
    async def cancel_open_orders(self, symbol: str) -> int:
        """Cancel all open orders"""
        pass

    @abstractmethod
    async def change_leverage(self, symbol: str, leverage: int):
        """Change leverage"""
        pass

    @abstractmethod
    async def get_exchange_info(self) -> Dict:
        """Get exchange trading rules"""
        pass
