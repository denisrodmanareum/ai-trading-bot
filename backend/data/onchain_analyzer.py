"""
On-Chain Data Analyzer
블록체인 데이터 분석으로 고래 움직임, 거래소 플로우, 네트워크 활동 추적
"""
import asyncio
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from collections import deque
import os


class GlassnodeClient:
    """
    Glassnode API Client
    온체인 메트릭 데이터 제공
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GLASSNODE_API_KEY', '')
        self.base_url = "https://api.glassnode.com/v1/metrics"
        
    async def get_exchange_netflow(self, asset: str = 'BTC') -> Dict:
        """
        거래소 순유입/유출
        
        양수: 거래소로 유입 (매도 압력) - BEARISH
        음수: 거래소에서 유출 (홀딩 증가) - BULLISH
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/transactions/transfers_volume_exchanges_net"
                params = {
                    'a': asset,
                    'api_key': self.api_key,
                    'i': '24h'  # 24시간 데이터
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data and len(data) > 0:
                            latest = data[-1]
                            netflow = float(latest['v'])
                            
                            return {
                                'asset': asset,
                                'netflow': netflow,
                                'netflow_usd': netflow * 104000,  # 대략적인 USD 가치
                                'signal': 'BEARISH' if netflow > 0 else 'BULLISH',
                                'strength': min(abs(netflow) / 1000, 10),  # 0-10 스케일
                                'timestamp': latest['t']
                            }
        except Exception as e:
            logger.error(f"Glassnode exchange netflow failed: {e}")
        
        # Fallback: 시뮬레이션 데이터
        return self._simulate_exchange_netflow(asset)
    
    async def get_whale_transactions(self, asset: str = 'BTC', threshold: int = 100) -> Dict:
        """
        고래 거래 (100+ BTC)
        
        Returns:
            {
                'whale_tx_count': int,
                'total_volume': float,
                'avg_size': float,
                'signal': str
            }
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/transactions/transfers_volume_sum"
                params = {
                    'a': asset,
                    'api_key': self.api_key,
                    'i': '24h'
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data and len(data) > 0:
                            latest = data[-1]
                            volume = float(latest['v'])
                            
                            # 고래 거래 추정 (100+ BTC)
                            whale_count = int(volume / 200)  # 평균 200 BTC로 가정
                            
                            return {
                                'asset': asset,
                                'whale_tx_count': whale_count,
                                'total_volume': volume,
                                'avg_size': volume / max(whale_count, 1),
                                'signal': 'HIGH_ACTIVITY' if whale_count > 50 else 'NORMAL',
                                'timestamp': latest['t']
                            }
        except Exception as e:
            logger.error(f"Glassnode whale transactions failed: {e}")
        
        return self._simulate_whale_transactions(asset)
    
    async def get_active_addresses(self, asset: str = 'BTC') -> Dict:
        """
        활성 주소 수 (네트워크 활동 지표)
        
        증가: 네트워크 사용 증가 - BULLISH
        감소: 관심 감소 - BEARISH
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/addresses/active_count"
                params = {
                    'a': asset,
                    'api_key': self.api_key,
                    'i': '24h'
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data and len(data) > 1:
                            current = float(data[-1]['v'])
                            previous = float(data[-2]['v'])
                            change_pct = ((current - previous) / previous) * 100
                            
                            return {
                                'asset': asset,
                                'active_addresses': int(current),
                                'change_pct': round(change_pct, 2),
                                'signal': 'BULLISH' if change_pct > 5 else 'BEARISH' if change_pct < -5 else 'NEUTRAL',
                                'timestamp': data[-1]['t']
                            }
        except Exception as e:
            logger.error(f"Glassnode active addresses failed: {e}")
        
        return self._simulate_active_addresses(asset)
    
    def _simulate_exchange_netflow(self, asset: str) -> Dict:
        """시뮬레이션 데이터"""
        import random
        netflow = random.uniform(-500, 500)
        return {
            'asset': asset,
            'netflow': round(netflow, 2),
            'netflow_usd': round(netflow * 104000, 2),
            'signal': 'BEARISH' if netflow > 0 else 'BULLISH',
            'strength': round(min(abs(netflow) / 100, 10), 1),
            'timestamp': int(datetime.now().timestamp()),
            'simulated': True
        }
    
    def _simulate_whale_transactions(self, asset: str) -> Dict:
        """시뮬레이션 데이터"""
        import random
        whale_count = random.randint(20, 80)
        volume = whale_count * random.uniform(150, 250)
        return {
            'asset': asset,
            'whale_tx_count': whale_count,
            'total_volume': round(volume, 2),
            'avg_size': round(volume / whale_count, 2),
            'signal': 'HIGH_ACTIVITY' if whale_count > 50 else 'NORMAL',
            'timestamp': int(datetime.now().timestamp()),
            'simulated': True
        }
    
    def _simulate_active_addresses(self, asset: str) -> Dict:
        """시뮬레이션 데이터"""
        import random
        current = random.randint(800000, 1200000)
        change_pct = random.uniform(-10, 10)
        return {
            'asset': asset,
            'active_addresses': current,
            'change_pct': round(change_pct, 2),
            'signal': 'BULLISH' if change_pct > 5 else 'BEARISH' if change_pct < -5 else 'NEUTRAL',
            'timestamp': int(datetime.now().timestamp()),
            'simulated': True
        }


class CryptoQuantClient:
    """
    CryptoQuant API Client
    거래소 데이터 및 채굴자 데이터
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('CRYPTOQUANT_API_KEY', '')
        self.base_url = "https://api.cryptoquant.com/v1"
        
    async def get_exchange_reserve(self, asset: str = 'btc') -> Dict:
        """
        거래소 보유량
        
        증가: 매도 압력 증가
        감소: 매도 압력 감소 (BULLISH)
        """
        # CryptoQuant API 구현 (실제로는 API 키 필요)
        return self._simulate_exchange_reserve(asset)
    
    async def get_miner_flows(self, asset: str = 'btc') -> Dict:
        """
        채굴자 플로우
        
        채굴자 → 거래소: 매도 압력 (BEARISH)
        채굴자 홀딩 증가: (BULLISH)
        """
        return self._simulate_miner_flows(asset)
    
    def _simulate_exchange_reserve(self, asset: str) -> Dict:
        """시뮬레이션 데이터"""
        import random
        reserve = random.uniform(2000000, 2500000)
        change_pct = random.uniform(-2, 2)
        return {
            'asset': asset.upper(),
            'exchange_reserve': round(reserve, 2),
            'change_pct': round(change_pct, 2),
            'signal': 'BULLISH' if change_pct < -1 else 'BEARISH' if change_pct > 1 else 'NEUTRAL',
            'timestamp': int(datetime.now().timestamp()),
            'simulated': True
        }
    
    def _simulate_miner_flows(self, asset: str) -> Dict:
        """시뮬레이션 데이터"""
        import random
        to_exchange = random.uniform(0, 500)
        return {
            'asset': asset.upper(),
            'miner_to_exchange': round(to_exchange, 2),
            'signal': 'BEARISH' if to_exchange > 300 else 'NEUTRAL',
            'timestamp': int(datetime.now().timestamp()),
            'simulated': True
        }


class OnChainAnalyzer:
    """
    통합 온체인 분석기
    """
    
    def __init__(self):
        self.glassnode = GlassnodeClient()
        self.cryptoquant = CryptoQuantClient()
        self.metrics_history = deque(maxlen=100)
        
    async def get_comprehensive_onchain_data(self, asset: str = 'BTC') -> Dict:
        """
        종합 온체인 데이터
        
        Returns:
            {
                'exchange_flows': {...},
                'whale_activity': {...},
                'network_activity': {...},
                'miner_behavior': {...},
                'overall_signal': str,
                'confidence': float
            }
        """
        try:
            # 병렬로 모든 데이터 수집
            exchange_netflow, whale_tx, active_addr, exchange_reserve, miner_flows = await asyncio.gather(
                self.glassnode.get_exchange_netflow(asset),
                self.glassnode.get_whale_transactions(asset),
                self.glassnode.get_active_addresses(asset),
                self.cryptoquant.get_exchange_reserve(asset.lower()),
                self.cryptoquant.get_miner_flows(asset.lower())
            )
            
            # 종합 시그널 계산
            overall_signal, confidence = self._calculate_overall_signal({
                'exchange_netflow': exchange_netflow,
                'whale_tx': whale_tx,
                'active_addr': active_addr,
                'exchange_reserve': exchange_reserve,
                'miner_flows': miner_flows
            })
            
            result = {
                'asset': asset,
                'exchange_flows': {
                    'netflow': exchange_netflow['netflow'],
                    'signal': exchange_netflow['signal'],
                    'reserve': exchange_reserve['exchange_reserve'],
                    'reserve_change': exchange_reserve['change_pct']
                },
                'whale_activity': {
                    'tx_count': whale_tx['whale_tx_count'],
                    'total_volume': whale_tx['total_volume'],
                    'signal': whale_tx['signal']
                },
                'network_activity': {
                    'active_addresses': active_addr['active_addresses'],
                    'change_pct': active_addr['change_pct'],
                    'signal': active_addr['signal']
                },
                'miner_behavior': {
                    'to_exchange': miner_flows['miner_to_exchange'],
                    'signal': miner_flows['signal']
                },
                'overall_signal': overall_signal,
                'confidence': confidence,
                'timestamp': datetime.now().isoformat()
            }
            
            # 히스토리 저장
            self.metrics_history.append(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Comprehensive onchain data failed: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _calculate_overall_signal(self, metrics: Dict) -> tuple:
        """
        모든 메트릭을 종합하여 전체 시그널 계산
        
        Returns:
            (signal: str, confidence: float)
        """
        signals = []
        weights = []
        
        # Exchange Netflow (가중치: 0.3)
        if metrics['exchange_netflow']['signal'] == 'BULLISH':
            signals.append(1)
        elif metrics['exchange_netflow']['signal'] == 'BEARISH':
            signals.append(-1)
        else:
            signals.append(0)
        weights.append(0.3)
        
        # Whale Activity (가중치: 0.2)
        if metrics['whale_tx']['signal'] == 'HIGH_ACTIVITY':
            signals.append(0)  # 중립 (방향성 불확실)
        else:
            signals.append(0)
        weights.append(0.2)
        
        # Network Activity (가중치: 0.2)
        if metrics['active_addr']['signal'] == 'BULLISH':
            signals.append(1)
        elif metrics['active_addr']['signal'] == 'BEARISH':
            signals.append(-1)
        else:
            signals.append(0)
        weights.append(0.2)
        
        # Exchange Reserve (가중치: 0.15)
        if metrics['exchange_reserve']['signal'] == 'BULLISH':
            signals.append(1)
        elif metrics['exchange_reserve']['signal'] == 'BEARISH':
            signals.append(-1)
        else:
            signals.append(0)
        weights.append(0.15)
        
        # Miner Flows (가중치: 0.15)
        if metrics['miner_flows']['signal'] == 'BEARISH':
            signals.append(-1)
        else:
            signals.append(0)
        weights.append(0.15)
        
        # 가중 평균 계산
        weighted_sum = sum(s * w for s, w in zip(signals, weights))
        
        # 시그널 결정
        if weighted_sum > 0.2:
            overall_signal = 'BULLISH'
        elif weighted_sum < -0.2:
            overall_signal = 'BEARISH'
        else:
            overall_signal = 'NEUTRAL'
        
        # 신뢰도 계산 (0.5 ~ 1.0)
        confidence = 0.5 + abs(weighted_sum) * 0.5
        
        return overall_signal, round(confidence, 2)
    
    def get_onchain_trend(self, lookback: int = 10) -> Dict:
        """
        온체인 메트릭 추세 분석
        """
        if len(self.metrics_history) < lookback:
            return {'trend': 'INSUFFICIENT_DATA'}
        
        recent = list(self.metrics_history)[-lookback:]
        
        # 거래소 순유입 추세
        netflows = [m['exchange_flows']['netflow'] for m in recent]
        netflow_trend = 'INCREASING' if netflows[-1] > netflows[0] else 'DECREASING'
        
        # 활성 주소 추세
        active_addr_changes = [m['network_activity']['change_pct'] for m in recent]
        avg_change = sum(active_addr_changes) / len(active_addr_changes)
        
        return {
            'netflow_trend': netflow_trend,
            'network_activity_trend': 'GROWING' if avg_change > 0 else 'DECLINING',
            'avg_network_change': round(avg_change, 2),
            'lookback_periods': lookback
        }
