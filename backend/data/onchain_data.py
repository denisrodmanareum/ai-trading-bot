"""
OnChain Data Analyzer
온체인 데이터: 고래 움직임, 거래소 유출입, 펀딩 레이트 등
"""
from typing import Dict, List, Optional
import aiohttp
from loguru import logger
from datetime import datetime, timedelta


class OnChainDataAnalyzer:
    """
    온체인 데이터 분석
    - Whale Alert API (고래 움직임)
    - Exchange Netflow
    - Funding Rate
    """
    
    def __init__(self):
        # Whale Alert API (무료 티어 제한적)
        self.whale_alert_base = "https://api.whale-alert.io/v1"
        self.whale_alert_key = "demo"  # 실제 사용 시 API 키 필요
        
        # Exchange API for funding rate
        self.public_api_base = "https://fapi.binance.com/fapi/v1"
    
    async def get_whale_activities(self, hours_ago: int = 24, min_usd: int = 1000000) -> List[Dict]:
        """
        고래 거래 활동 조회
        
        Args:
            hours_ago: 몇 시간 전까지
            min_usd: 최소 금액 (USD)
        
        Returns:
            List of whale transactions
        """
        try:
            # Calculate time range
            end_time = int(datetime.now().timestamp())
            start_time = int((datetime.now() - timedelta(hours=hours_ago)).timestamp())
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.whale_alert_base}/transactions"
                params = {
                    'api_key': self.whale_alert_key,
                    'start': start_time,
                    'end': end_time,
                    'min_value': min_usd
                }
                
                # Note: Demo key has limitations
                # For production, use actual API key
                
                # Fallback mock data for demo
                return self._get_mock_whale_data()
                
        except Exception as e:
            logger.error(f"Failed to fetch whale activities: {e}")
            return self._get_mock_whale_data()
    
    def _get_mock_whale_data(self) -> List[Dict]:
        """Mock whale data for demonstration"""
        import random
        
        exchanges = ['Exchange', 'Coinbase', 'Kraken', 'unknown wallet']
        cryptos = ['BTC', 'ETH', 'USDT', 'USDC']
        
        whale_transactions = []
        for i in range(10):
            crypto = random.choice(cryptos)
            from_owner = random.choice(exchanges)
            to_owner = random.choice(exchanges)
            
            if crypto == 'BTC':
                amount = random.randint(100, 1000)
                amount_usd = amount * 104000
            elif crypto == 'ETH':
                amount = random.randint(1000, 10000)
                amount_usd = amount * 3400
            else:
                amount = random.randint(1000000, 50000000)
                amount_usd = amount
            
            # Determine transaction type
            if 'unknown' in from_owner:
                tx_type = 'deposit' if to_owner != 'unknown wallet' else 'transfer'
            elif 'unknown' in to_owner:
                tx_type = 'withdrawal'
            else:
                tx_type = 'exchange_transfer'
            
            whale_transactions.append({
                'blockchain': 'ethereum' if crypto == 'ETH' else 'bitcoin',
                'symbol': crypto,
                'amount': amount,
                'amount_usd': amount_usd,
                'from': from_owner,
                'to': to_owner,
                'timestamp': (datetime.now() - timedelta(minutes=random.randint(10, 1440))).isoformat(),
                'hash': f"0x{''.join(random.choices('0123456789abcdef', k=64))}",
                'transaction_type': tx_type
            })
        
        # Sort by timestamp (newest first)
        whale_transactions.sort(key=lambda x: x['timestamp'], reverse=True)
        return whale_transactions
    
    async def get_exchange_netflow(self, symbol: str = 'BTC') -> Dict:
        """
        거래소 유입/유출 (Netflow)
        
        Args:
            symbol: 코인 심볼
        
        Returns:
            Exchange netflow data
        """
        try:
            # This would typically fetch from CryptoQuant or Glassnode API
            # For now, return mock data
            
            import random
            
            # Generate mock netflow data
            netflow_24h = random.randint(-5000, 5000)  # Negative = outflow
            netflow_7d = random.randint(-20000, 20000)
            
            return {
                'symbol': symbol,
                'netflow_24h': netflow_24h,
                'netflow_7d': netflow_7d,
                'trend': 'outflow' if netflow_24h < 0 else 'inflow',
                'signal': self._interpret_netflow(netflow_24h),
                'exchange_balance': random.randint(100000, 500000),
                'updated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get exchange netflow: {e}")
            return {}
    
    def _interpret_netflow(self, netflow: float) -> str:
        """Interpret netflow signal"""
        if netflow < -1000:
            return '🚀 Strong Bullish (Large Outflow)'
        elif netflow < 0:
            return '📈 Bullish (Outflow)'
        elif netflow > 1000:
            return '📉 Bearish (Large Inflow)'
        elif netflow > 0:
            return '⚠️ Cautious (Inflow)'
        else:
            return '😐 Neutral'
    
    async def get_funding_rates(self) -> List[Dict]:
        """
        펀딩 레이트 조회 (Exchange Futures)
        
        Returns:
            List of funding rates for major pairs
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.public_api_base}/premiumIndex"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Filter major pairs
                        major_pairs = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']
                        funding_rates = []
                        
                        for item in data:
                            symbol = item.get('symbol', '')
                            if symbol in major_pairs:
                                funding_rate = float(item.get('lastFundingRate', 0))
                                
                                # Interpret funding rate
                                if funding_rate > 0.01:
                                    signal = 'Very Bullish (High Long Interest)'
                                    emoji = '🚀'
                                elif funding_rate > 0:
                                    signal = 'Bullish'
                                    emoji = '📈'
                                elif funding_rate < -0.01:
                                    signal = 'Very Bearish (High Short Interest)'
                                    emoji = '📉'
                                elif funding_rate < 0:
                                    signal = 'Bearish'
                                    emoji = '⚠️'
                                else:
                                    signal = 'Neutral'
                                    emoji = '😐'
                                
                                funding_rates.append({
                                    'symbol': symbol,
                                    'funding_rate': funding_rate * 100,  # Convert to percentage
                                    'next_funding_time': item.get('nextFundingTime', 0),
                                    'signal': signal,
                                    'emoji': emoji,
                                    'mark_price': float(item.get('markPrice', 0)),
                                    'index_price': float(item.get('indexPrice', 0))
                                })
                        
                        return funding_rates
        except Exception as e:
            logger.error(f"Failed to fetch funding rates: {e}")
        
        return []
    
    async def get_open_interest(self, symbol: str = 'BTCUSDT') -> Dict:
        """
        Open Interest 조회
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            Open interest data
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.public_api_base}/openInterest"
                params = {'symbol': symbol}
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        oi_value = float(data.get('openInterest', 0))
                        
                        return {
                            'symbol': symbol,
                            'open_interest': oi_value,
                            'timestamp': data.get('time', 0),
                            'updated_at': datetime.now().isoformat()
                        }
        except Exception as e:
            logger.error(f"Failed to fetch open interest for {symbol}: {e}")
        
        return {}
    
    async def get_long_short_ratio(self, symbol: str = 'BTCUSDT') -> Dict:
        """
        Long/Short Ratio 조회
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            Long/Short ratio data
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.public_api_base}/globalLongShortAccountRatio"
                params = {
                    'symbol': symbol,
                    'period': '5m',
                    'limit': 1
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data:
                            latest = data[0]
                            long_ratio = float(latest.get('longAccount', 0))
                            short_ratio = float(latest.get('shortAccount', 0))
                            
                            # Interpret ratio
                            if long_ratio > 0.6:
                                signal = 'Bullish Majority'
                                emoji = '📈'
                            elif short_ratio > 0.6:
                                signal = 'Bearish Majority'
                                emoji = '📉'
                            else:
                                signal = 'Balanced'
                                emoji = '😐'
                            
                            return {
                                'symbol': symbol,
                                'long_ratio': long_ratio * 100,
                                'short_ratio': short_ratio * 100,
                                'signal': signal,
                                'emoji': emoji,
                                'timestamp': latest.get('timestamp', 0),
                                'updated_at': datetime.now().isoformat()
                            }
        except Exception as e:
            logger.error(f"Failed to fetch long/short ratio for {symbol}: {e}")
        
        return {}


# Global instance
onchain_data_analyzer = OnChainDataAnalyzer()
