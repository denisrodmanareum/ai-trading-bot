"""
Market Data Aggregator
시장 데이터, Fear & Greed Index, Market Cap 등
"""
from typing import Dict, List, Optional
import aiohttp
from loguru import logger
from datetime import datetime


class MarketDataAggregator:
    """
    시장 데이터 수집
    - CoinGecko API (무료)
    - Fear & Greed Index
    - Global Market Stats
    """
    
    def __init__(self):
        self.coingecko_base = "https://api.coingecko.com/api/v3"
        self.fear_greed_url = "https://api.alternative.me/fng/"
        
    async def get_market_overview(self) -> Dict:
        """
        전체 시장 개요
        
        Returns:
            {
                'total_market_cap': float,
                'total_volume': float,
                'btc_dominance': float,
                'eth_dominance': float,
                'fear_greed_index': int,
                'fear_greed_label': str,
                'trending_coins': list,
                'top_gainers': list,
                'top_losers': list
            }
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Fetch global data
                global_data = await self._fetch_global_data(session)
                
                # Fetch fear & greed index
                fear_greed = await self._fetch_fear_greed(session)
                
                # Fetch trending coins
                trending = await self._fetch_trending_coins(session)
                
                # Fetch top gainers/losers
                gainers_losers = await self._fetch_gainers_losers(session)
                
                return {
                    'total_market_cap': global_data.get('total_market_cap', {}).get('usd', 0),
                    'total_volume': global_data.get('total_volume', {}).get('usd', 0),
                    'btc_dominance': global_data.get('market_cap_percentage', {}).get('btc', 0),
                    'eth_dominance': global_data.get('market_cap_percentage', {}).get('eth', 0),
                    'active_cryptocurrencies': global_data.get('active_cryptocurrencies', 0),
                    'markets': global_data.get('markets', 0),
                    'fear_greed_index': fear_greed.get('value', 50),
                    'fear_greed_label': fear_greed.get('label', 'Neutral'),
                    'trending_coins': trending,
                    'top_gainers': gainers_losers.get('gainers', []),
                    'top_losers': gainers_losers.get('losers', []),
                    'updated_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get market overview: {e}")
            return self._get_fallback_data()
    
    async def _fetch_global_data(self, session: aiohttp.ClientSession) -> Dict:
        """CoinGecko Global Data"""
        try:
            async with session.get(f"{self.coingecko_base}/global") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', {})
        except Exception as e:
            logger.error(f"Failed to fetch global data: {e}")
        return {}
    
    async def _fetch_fear_greed(self, session: aiohttp.ClientSession) -> Dict:
        """
        Fear & Greed Index
        0-100: 0 = Extreme Fear, 100 = Extreme Greed
        """
        try:
            async with session.get(self.fear_greed_url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('data'):
                        latest = data['data'][0]
                        value = int(latest.get('value', 50))
                        
                        # Determine label
                        if value < 20:
                            label = 'Extreme Fear'
                            emoji = '😱'
                        elif value < 40:
                            label = 'Fear'
                            emoji = '😰'
                        elif value < 60:
                            label = 'Neutral'
                            emoji = '😐'
                        elif value < 80:
                            label = 'Greed'
                            emoji = '😊'
                        else:
                            label = 'Extreme Greed'
                            emoji = '🤑'
                        
                        return {
                            'value': value,
                            'label': label,
                            'emoji': emoji,
                            'classification': latest.get('value_classification', 'Neutral')
                        }
        except Exception as e:
            logger.error(f"Failed to fetch fear & greed: {e}")
        
        return {'value': 50, 'label': 'Neutral', 'emoji': '😐'}
    
    async def _fetch_trending_coins(self, session: aiohttp.ClientSession) -> List[Dict]:
        """CoinGecko Trending Coins"""
        try:
            async with session.get(f"{self.coingecko_base}/search/trending") as response:
                if response.status == 200:
                    data = await response.json()
                    coins = data.get('coins', [])
                    
                    trending = []
                    for item in coins[:7]:  # Top 7
                        coin = item.get('item', {})
                        trending.append({
                            'name': coin.get('name', ''),
                            'symbol': coin.get('symbol', '').upper(),
                            'market_cap_rank': coin.get('market_cap_rank', 0),
                            'price_btc': coin.get('price_btc', 0),
                            'thumb': coin.get('thumb', '')
                        })
                    
                    return trending
        except Exception as e:
            logger.error(f"Failed to fetch trending coins: {e}")
        return []
    
    async def _fetch_gainers_losers(self, session: aiohttp.ClientSession) -> Dict:
        """Top Gainers and Losers (24h)"""
        try:
            # Fetch top 100 coins with 24h change
            url = f"{self.coingecko_base}/coins/markets"
            params = {
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': 100,
                'page': 1,
                'sparkline': 'false',
                'price_change_percentage': '24h'
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    coins = await response.json()
                    
                    # Filter out coins with None price_change_percentage_24h
                    valid_coins = [
                        coin for coin in coins 
                        if coin.get('price_change_percentage_24h') is not None
                    ]
                    
                    # Sort by 24h change
                    sorted_coins = sorted(
                        valid_coins,
                        key=lambda x: x.get('price_change_percentage_24h', 0),
                        reverse=True
                    )
                    
                    # Top gainers
                    gainers = [
                        {
                            'name': coin.get('name', 'Unknown'),
                            'symbol': coin.get('symbol', '').upper(),
                            'price': coin.get('current_price', 0),
                            'change_24h': coin.get('price_change_percentage_24h', 0),
                            'market_cap': coin.get('market_cap', 0),
                            'image': coin.get('image', '')
                        }
                        for coin in sorted_coins[:5] if coin.get('current_price')
                    ]
                    
                    # Top losers
                    losers = [
                        {
                            'name': coin.get('name', 'Unknown'),
                            'symbol': coin.get('symbol', '').upper(),
                            'price': coin.get('current_price', 0),
                            'change_24h': coin.get('price_change_percentage_24h', 0),
                            'market_cap': coin.get('market_cap', 0),
                            'image': coin.get('image', '')
                        }
                        for coin in sorted_coins[-5:][::-1] if coin.get('current_price')
                    ]
                    
                    return {'gainers': gainers, 'losers': losers}
        except Exception as e:
            logger.error(f"Failed to fetch gainers/losers: {e}")
        
        return {'gainers': [], 'losers': []}
    
    async def get_coin_market_data(self, symbol: str) -> Dict:
        """
        특정 코인의 상세 시장 데이터
        
        Args:
            symbol: 코인 심볼 (e.g., 'BTC', 'ETH')
        
        Returns:
            Detailed market data for the coin
        """
        try:
            # Map symbol to CoinGecko ID
            symbol_map = {
                'BTC': 'bitcoin',
                'ETH': 'ethereum',
                'SOL': 'solana',
                'BNB': 'binancecoin',
                'XRP': 'ripple',
                'ADA': 'cardano',
                'DOGE': 'dogecoin',
                'AVAX': 'avalanche-2',
                'MATIC': 'matic-network',
                'DOT': 'polkadot'
            }
            
            coin_id = symbol_map.get(symbol.upper(), symbol.lower())
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.coingecko_base}/coins/{coin_id}"
                params = {
                    'localization': 'false',
                    'tickers': 'false',
                    'market_data': 'true',
                    'community_data': 'false',
                    'developer_data': 'false'
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        market_data = data.get('market_data', {})
                        
                        return {
                            'name': data.get('name', ''),
                            'symbol': data.get('symbol', '').upper(),
                            'current_price': market_data.get('current_price', {}).get('usd', 0),
                            'market_cap': market_data.get('market_cap', {}).get('usd', 0),
                            'market_cap_rank': data.get('market_cap_rank', 0),
                            'total_volume': market_data.get('total_volume', {}).get('usd', 0),
                            'high_24h': market_data.get('high_24h', {}).get('usd', 0),
                            'low_24h': market_data.get('low_24h', {}).get('usd', 0),
                            'price_change_24h': market_data.get('price_change_24h', 0),
                            'price_change_percentage_24h': market_data.get('price_change_percentage_24h', 0),
                            'circulating_supply': market_data.get('circulating_supply', 0),
                            'total_supply': market_data.get('total_supply', 0),
                            'ath': market_data.get('ath', {}).get('usd', 0),
                            'ath_date': market_data.get('ath_date', {}).get('usd', ''),
                            'atl': market_data.get('atl', {}).get('usd', 0),
                            'atl_date': market_data.get('atl_date', {}).get('usd', '')
                        }
        except Exception as e:
            logger.error(f"Failed to get coin market data for {symbol}: {e}")
        
        return {}
    
    def _get_fallback_data(self) -> Dict:
        """Fallback data when API fails"""
        return {
            'total_market_cap': 3200000000000,
            'total_volume': 180000000000,
            'btc_dominance': 54.2,
            'eth_dominance': 17.3,
            'active_cryptocurrencies': 12000,
            'markets': 800,
            'fear_greed_index': 50,
            'fear_greed_label': 'Neutral',
            'trending_coins': [],
            'top_gainers': [],
            'top_losers': [],
            'updated_at': datetime.now().isoformat()
        }


# Global instance
market_data_aggregator = MarketDataAggregator()
