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
            'mode': 'BTC_ONLY',  # 🆕 BTC_ONLY or HYBRID (Default changed to BTC_ONLY)
            'core_coins': ['BTC', 'ETH', 'SOL', 'BNB'],
            'max_altcoins': 3,
            'max_total': 7,
            'rebalance_interval_hours': 1,
            'filters': {
                'min_market_cap_usd': 1_000_000_000,  # $1B
                'min_volume_24h_usd': 100_000_000,    # $100M
                'min_price_change_24h': -50,           # Don't select coins down > 50%
                'max_price_change_24h': 100,           # Or up > 100% (pump & dump risk)
                'min_liquidity_score': 7               # Out of 10
            },
            'scoring': {
                'volume_weight': 0.3,
                'volatility_weight': 0.3,
                'momentum_weight': 0.2,
                'liquidity_weight': 0.2
            }
        }
        
        # Initialize with fallback coins (important for first run)
        # BTC Only 모드에 맞춰 초기화
        self.selected_coins = ['BTCUSDT']
        self.last_rebalance = datetime.now()
        self.coin_scores = {'BTCUSDT': 100.0}
    
    async def get_selected_coins(self) -> List[str]:
        """
        Get currently selected coins
        Returns: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', ...]
        """
        # 🆕 BTC Only 모드: 비트코인만 반환
        if self.config.get('mode') == 'BTC_ONLY':
            logger.debug("₿ BTC Only Mode: Returning BTCUSDT only")
            return ['BTCUSDT']
        
        # HYBRID 모드: 기존 로직
        # Check if rebalance needed
        if self._should_rebalance():
            await self.rebalance()
        
        return self.selected_coins
    
    def _should_rebalance(self) -> bool:
        """Check if it's time to rebalance"""
        if not self.last_rebalance:
            return True
        
        hours_passed = (datetime.now() - self.last_rebalance).total_seconds() / 3600
        return hours_passed >= self.config['rebalance_interval_hours']
    
    async def rebalance(self) -> Dict:
        """
        Rebalance coin selection
        1. Always include core coins (BTC, ETH)
        2. Auto-select top altcoins based on criteria
        
        Returns:
            {
                'selected_coins': [...],
                'scores': {...},
                'timestamp': '...'
            }
        """
        # 🆕 BTC Only 모드: 재선별 불필요
        if self.config.get('mode') == 'BTC_ONLY':
            logger.info("₿ BTC Only Mode: No rebalancing needed")
            self.selected_coins = ['BTCUSDT']
            self.coin_scores = {'BTCUSDT': 100.0}
            self.last_rebalance = datetime.now()
            return {
                'mode': 'BTC_ONLY',
                'selected_coins': self.selected_coins,
                'scores': self.coin_scores,
                'message': 'BTC Only Mode - Bitcoin All-In Strategy'
            }
        
        logger.info("🔄 Rebalancing coin selection... (HYBRID Mode)")
        
        try:
            # Get all available futures symbols from Exchange
            futures_symbols = await self._get_exchange_futures_symbols()
            
            # Get market data from CoinGecko
            market_data = await self._get_coingecko_market_data()
            
            # Score and rank coins
            scored_coins = await self._score_coins(futures_symbols, market_data)
            
            # Select coins
            selected = self._select_coins(scored_coins)
            
            self.selected_coins = selected['coins']
            self.coin_scores = selected['scores']
            self.last_rebalance = datetime.now()
            
            logger.info(f"✅ Rebalanced! Selected: {self.selected_coins}")
            
            return {
                'selected_coins': self.selected_coins,
                'scores': self.coin_scores,
                'timestamp': self.last_rebalance.isoformat(),
                'next_rebalance': (self.last_rebalance + timedelta(hours=self.config['rebalance_interval_hours'])).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to rebalance: {e}")
            # Fallback to default
            return self._get_fallback_selection()
    
    async def _get_exchange_futures_symbols(self) -> List[str]:
        """Get all USDT futures symbols from Exchange"""
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{self.public_api_base}/exchangeInfo"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        symbols = [
                            s['symbol'] for s in data.get('symbols', [])
                            if s['symbol'].endswith('USDT') and s['status'] == 'TRADING'
                        ]
                        logger.info(f"Found {len(symbols)} active USDT futures pairs")
                        return symbols
        except Exception as e:
            logger.error(f"Failed to get Exchange symbols: {e}")
        
        return []
    
    async def _get_coingecko_market_data(self) -> List[Dict]:
        """Get market data from CoinGecko"""
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
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
                        data = await response.json()
                        logger.info(f"Fetched {len(data)} coins from CoinGecko")
                        return data
        except Exception as e:
            logger.error(f"Failed to get CoinGecko data: {e}")
        
        return []
    
    async def _score_coins(self, exchange_symbols: List[str], coingecko_data: List[Dict]) -> List[Dict]:
        """
        Score coins based on multiple criteria
        
        Returns:
            [
                {
                    'symbol': 'SOLUSDT',
                    'score': 85.5,
                    'metrics': {...}
                },
                ...
            ]
        """
        scored = []
        
        # Symbol mapping
        symbol_map = {
            'bitcoin': 'BTC',
            'ethereum': 'ETH',
            'solana': 'SOL',
            'binancecoin': 'BNB',
            'ripple': 'XRP',
            'cardano': 'ADA',
            'avalanche-2': 'AVAX',
            'matic-network': 'MATIC',
            'polkadot': 'DOT',
            'chainlink': 'LINK',
            'dogecoin': 'DOGE',
            'shiba-inu': 'SHIB',
            'litecoin': 'LTC',
            'uniswap': 'UNI',
            'cosmos': 'ATOM'
        }
        
        for coin in coingecko_data:
            try:
                coin_id = coin.get('id', '')
                symbol = symbol_map.get(coin_id, coin.get('symbol', '').upper())
                exchange_symbol = f"{symbol}USDT"
                
                # Check if available on Exchange Futures
                if exchange_symbol not in exchange_symbols:
                    continue
                
                # Apply filters
                market_cap = coin.get('market_cap', 0)
                volume_24h = coin.get('total_volume', 0)
                price_change_24h = coin.get('price_change_percentage_24h')
                
                if market_cap < self.config['filters']['min_market_cap_usd']:
                    continue
                if volume_24h < self.config['filters']['min_volume_24h_usd']:
                    continue
                if price_change_24h is None:
                    continue
                if price_change_24h < self.config['filters']['min_price_change_24h']:
                    continue
                if price_change_24h > self.config['filters']['max_price_change_24h']:
                    continue
                
                # Calculate score
                score = self._calculate_score(coin)
                
                scored.append({
                    'symbol': exchange_symbol,
                    'base_symbol': symbol,
                    'score': score,
                    'metrics': {
                        'market_cap': market_cap,
                        'volume_24h': volume_24h,
                        'price_change_24h': price_change_24h,
                        'current_price': coin.get('current_price', 0),
                        'market_cap_rank': coin.get('market_cap_rank', 999)
                    }
                })
                
            except Exception as e:
                logger.error(f"Error scoring coin {coin.get('symbol', 'unknown')}: {e}")
                continue
        
        # Sort by score
        scored.sort(key=lambda x: x['score'], reverse=True)
        
        return scored
    
    def _calculate_score(self, coin: Dict) -> float:
        """
        Calculate composite score for a coin
        
        Factors:
        - Volume (30%): Higher volume = higher score
        - Volatility (30%): Moderate volatility preferred
        - Momentum (20%): Positive momentum = higher score
        - Liquidity (20%): Better liquidity = higher score
        """
        weights = self.config['scoring']
        
        # Volume score (0-100)
        volume = coin.get('total_volume', 0)
        volume_score = min(100, (volume / 500_000_000) * 100)  # Max at $500M
        
        # Volatility score (0-100) - prefer moderate volatility (3-10%)
        price_change = abs(coin.get('price_change_percentage_24h', 0))
        if 3 <= price_change <= 10:
            volatility_score = 100
        elif price_change < 3:
            volatility_score = 50 + (price_change / 3) * 50
        else:
            volatility_score = max(0, 100 - (price_change - 10) * 5)
        
        # Momentum score (0-100) - prefer positive momentum
        momentum = coin.get('price_change_percentage_24h', 0)
        if momentum > 0:
            momentum_score = min(100, 50 + momentum * 5)
        else:
            momentum_score = max(0, 50 + momentum * 5)
        
        # Liquidity score (0-100) - based on market cap rank
        rank = coin.get('market_cap_rank', 100)
        liquidity_score = max(0, 100 - rank)
        
        # Weighted average
        total_score = (
            volume_score * weights['volume_weight'] +
            volatility_score * weights['volatility_weight'] +
            momentum_score * weights['momentum_weight'] +
            liquidity_score * weights['liquidity_weight']
        )
        
        return round(total_score, 2)
    
    def _select_coins(self, scored_coins: List[Dict]) -> Dict:
        """
        Select coins based on Hybrid strategy
        
        Returns:
            {
                'coins': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', ...],
                'scores': {'BTCUSDT': 95.5, ...}
            }
        """
        selected = []
        scores = {}
        
        # 1. Always include core coins
        core_symbols = [f"{c}USDT" for c in self.config['core_coins']]
        for symbol in core_symbols:
            selected.append(symbol)
            # Find score or default to high score
            coin_data = next((c for c in scored_coins if c['symbol'] == symbol), None)
            scores[symbol] = coin_data['score'] if coin_data else 95.0
        
        # 2. Auto-select top altcoins (exclude core coins)
        altcoins = [c for c in scored_coins if c['symbol'] not in core_symbols]
        max_alts = min(self.config['max_altcoins'], len(altcoins))
        
        for i in range(max_alts):
            if len(selected) >= self.config['max_total']:
                break
            
            coin = altcoins[i]
            selected.append(coin['symbol'])
            scores[coin['symbol']] = coin['score']
        
        return {
            'coins': selected,
            'scores': scores
        }
    
    def _get_fallback_selection(self) -> Dict:
        """Fallback when rebalance fails"""
        fallback = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT']
        
        return {
            'selected_coins': fallback,
            'scores': {s: 80.0 for s in fallback},
            'timestamp': datetime.now().isoformat(),
            'next_rebalance': (datetime.now() + timedelta(hours=1)).isoformat()
        }
    
    def update_config(self, new_config: Dict):
        """Update configuration"""
        self.config.update(new_config)
        logger.info(f"Configuration updated: {new_config}")
        
        # 🆕 모드 변경 시 즉시 적용
        if 'mode' in new_config:
            mode = new_config['mode']
            if mode == 'BTC_ONLY':
                self.selected_coins = ['BTCUSDT']
                self.coin_scores = {'BTCUSDT': 100.0}
                logger.info("₿ Switched to BTC Only Mode")
    
    def get_config(self) -> Dict:
        """Get current configuration"""
        return self.config.copy()


# Global instance
coin_selector = CoinSelector()
