"""
Hybrid Coin Selection Service
Core coins + Auto-selected high-potential altcoins
"""
from typing import List, Dict, Optional
import aiohttp
from loguru import logger
from datetime import datetime, timedelta
import asyncio


class CoinSelector:
    """
    Hybrid Coin Selection Strategy
    - Core coins: BTC, ETH (always included)
    - Auto-select: Top altcoins based on multiple criteria
    """
    
    def __init__(self):
        self.coingecko_base = "https://api.coingecko.com/api/v3"
        self.public_api_base = "https://fapi.binance.com/fapi/v1"
        
        # Default configuration
        self.config = {
            'max_coins': 5,  # 최대 선택 가능 코인 수
            'min_market_cap_usd': 1_000_000_000,  # $1B
            'min_volume_24h_usd': 100_000_000,    # $100M
        }
        
        # Initialize with default coins
        self.selected_coins = ['BTCUSDT', 'ETHUSDT']
        self.last_update = datetime.now()
    
    async def get_selected_coins(self) -> List[str]:
        """
        Get currently selected coins
        Returns: ['BTCUSDT', 'ETHUSDT', ...]
        """
        return self.selected_coins
    
    def set_selected_coins(self, coins: List[str]):
        """사용자가 선택한 코인 설정"""
        if len(coins) > self.config['max_coins']:
            raise ValueError(f"최대 {self.config['max_coins']}개까지 선택 가능합니다")
        
        if len(coins) == 0:
            raise ValueError("최소 1개 이상의 코인을 선택해야 합니다")
        
        # 유효성 검증 (USDT 페어인지 확인)
        for coin in coins:
            if not coin.endswith('USDT'):
                raise ValueError(f"Invalid symbol: {coin}. Must end with 'USDT'")
        
        self.selected_coins = coins
        self.last_update = datetime.now()
        logger.info(f"✅ 선택된 코인 업데이트: {self.selected_coins}")
    
    def get_status(self) -> Dict:
        """Get current selection status"""
        return {
            'selected_coins': self.selected_coins,
            'count': len(self.selected_coins),
            'max_coins': self.config['max_coins'],
            'last_update': self.last_update.isoformat()
        }
    
    def update_config(self, new_config: Dict):
        """Update configuration"""
        self.config.update(new_config)
        logger.info(f"Configuration updated: {new_config}")
    
    def get_config(self) -> Dict:
        """Get current configuration"""
        return self.config.copy()


# Global instance
coin_selector = CoinSelector()
