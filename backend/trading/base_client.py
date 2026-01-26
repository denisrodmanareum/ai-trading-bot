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

    @abstractmethod
    async def get_raw_klines(self, symbol: str, interval: str, limit: int, startTime: Optional[int] = None, endTime: Optional[int] = None) -> List[List]:
        """Get raw klines (list of lists)"""
        pass

    @abstractmethod
    async def get_mark_price(self, symbol: str) -> float:
        """Get mark price for symbol"""
        pass

    @abstractmethod
    async def get_mark_price_info(self, symbol: str) -> Dict:
        """Get comprehensive mark price info (mark, index, funding time)"""
        pass

    @abstractmethod
    async def get_24h_ticker(self, symbol: str) -> Dict:
        """Get 24h ticker data (high, low, volume)"""
        pass

    @abstractmethod
    async def get_recent_trades(self, symbol: str, limit: int) -> List[Dict]:
        """Get recent market trades"""
        pass

    @abstractmethod
    async def get_user_trades(self, symbol: str, limit: int = 50, startTime: Optional[int] = None, endTime: Optional[int] = None) -> List[Dict]:
        """Get user trade history with PnL"""
        pass
