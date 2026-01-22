"""
Quick Wins - 즉시 구현 가능한 시장 모니터링 기능
1. 김치 프리미엄 모니터링
2. 거래량 급증 감지
3. 고래 움직임 추적 (대량 전송)
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
import aiohttp
from collections import deque


class KimchiPremiumMonitor:
    """
    김치 프리미엄 모니터링
    Binance vs Upbit 가격 차이 추적
    """
    
    def __init__(self, alert_threshold: float = 2.0):
        """
        Args:
            alert_threshold: 알림 임계값 (%) 기본값 2%
        """
        self.alert_threshold = alert_threshold
        self.usd_krw_rate = 1300.0  # 환율 (업데이트 필요)
        self.premium_history = deque(maxlen=100)
        
    async def get_binance_price(self, symbol: str = 'BTCUSDT') -> Optional[float]:
        """Binance 현재가 조회"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return float(data['price'])
        except Exception as e:
            logger.error(f"Binance price fetch failed: {e}")
        return None
    
    async def get_upbit_price(self, symbol: str = 'KRW-BTC') -> Optional[float]:
        """Upbit 현재가 조회"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.upbit.com/v1/ticker?markets={symbol}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            return float(data[0]['trade_price'])
        except Exception as e:
            logger.error(f"Upbit price fetch failed: {e}")
        return None
    
    async def get_usd_krw_rate(self) -> float:
        """USD/KRW 환율 조회"""
        try:
            async with aiohttp.ClientSession() as session:
                # 간단한 환율 API 사용 (실제로는 더 안정적인 소스 사용)
                url = "https://api.exchangerate-api.com/v4/latest/USD"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return float(data['rates'].get('KRW', 1300.0))
        except Exception as e:
            logger.error(f"USD/KRW rate fetch failed: {e}")
        return 1300.0  # Fallback
    
    async def calculate_premium(self, base_symbol: str = 'BTC') -> Dict:
        """
        김치 프리미엄 계산
        
        Returns:
            {
                'binance_price': float,
                'upbit_price_usd': float,
                'premium_pct': float,
                'usd_krw_rate': float,
                'alert': bool,
                'timestamp': str
            }
        """
        # 환율 업데이트
        self.usd_krw_rate = await self.get_usd_krw_rate()
        
        # 가격 조회
        binance_symbol = f"{base_symbol}USDT"
        upbit_symbol = f"KRW-{base_symbol}"
        
        binance_price = await self.get_binance_price(binance_symbol)
        upbit_price_krw = await self.get_upbit_price(upbit_symbol)
        
        if binance_price is None or upbit_price_krw is None:
            return {
                'error': 'Failed to fetch prices',
                'timestamp': datetime.now().isoformat()
            }
        
        # Upbit 가격을 USD로 변환
        upbit_price_usd = upbit_price_krw / self.usd_krw_rate
        
        # 프리미엄 계산
        premium_pct = ((upbit_price_usd - binance_price) / binance_price) * 100
        
        # 알림 여부
        alert = abs(premium_pct) >= self.alert_threshold
        
        result = {
            'symbol': base_symbol,
            'binance_price': round(binance_price, 2),
            'upbit_price_krw': round(upbit_price_krw, 0),
            'upbit_price_usd': round(upbit_price_usd, 2),
            'usd_krw_rate': round(self.usd_krw_rate, 2),
            'premium_pct': round(premium_pct, 3),
            'alert': alert,
            'alert_message': self._generate_alert_message(premium_pct) if alert else None,
            'timestamp': datetime.now().isoformat()
        }
        
        # 히스토리 저장
        self.premium_history.append({
            'premium_pct': premium_pct,
            'timestamp': datetime.now()
        })
        
        if alert:
            logger.warning(f"🚨 김치 프리미엄 알림: {premium_pct:.2f}%")
        
        return result
    
    def _generate_alert_message(self, premium_pct: float) -> str:
        """알림 메시지 생성"""
        if premium_pct > 0:
            return f"🔥 김치 프리미엄 {premium_pct:.2f}%! Binance 매수 + Upbit 매도 차익거래 기회"
        else:
            return f"❄️ 역프리미엄 {abs(premium_pct):.2f}%! Upbit 매수 + Binance 매도 차익거래 기회"
    
    def get_premium_trend(self) -> Dict:
        """프리미엄 추세 분석"""
        if len(self.premium_history) < 10:
            return {'trend': 'INSUFFICIENT_DATA'}
        
        recent_10 = list(self.premium_history)[-10:]
        premiums = [h['premium_pct'] for h in recent_10]
        
        avg_premium = sum(premiums) / len(premiums)
        max_premium = max(premiums)
        min_premium = min(premiums)
        
        # 추세 판단
        if premiums[-1] > premiums[0]:
            trend = 'INCREASING'
        elif premiums[-1] < premiums[0]:
            trend = 'DECREASING'
        else:
            trend = 'STABLE'
        
        return {
            'trend': trend,
            'avg_premium': round(avg_premium, 2),
            'max_premium': round(max_premium, 2),
            'min_premium': round(min_premium, 2),
            'current_premium': round(premiums[-1], 2)
        }


class VolumeAnomalyDetector:
    """
    거래량 급증 감지
    평소 대비 비정상적인 거래량 탐지
    """
    
    def __init__(self, spike_threshold: float = 3.0):
        """
        Args:
            spike_threshold: 급증 임계값 (배수) 기본값 3배
        """
        self.spike_threshold = spike_threshold
        self.volume_history = {}  # {symbol: deque}
        
    async def get_current_volume(self, symbol: str = 'BTCUSDT') -> Optional[Dict]:
        """현재 거래량 조회"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'symbol': symbol,
                            'volume': float(data['volume']),
                            'quote_volume': float(data['quoteVolume']),
                            'trades': int(data['count']),
                            'timestamp': datetime.now().isoformat()
                        }
        except Exception as e:
            logger.error(f"Volume fetch failed: {e}")
        return None
    
    async def detect_volume_spike(self, symbol: str = 'BTCUSDT') -> Dict:
        """
        거래량 급증 감지
        
        Returns:
            {
                'symbol': str,
                'current_volume': float,
                'avg_volume': float,
                'spike_ratio': float,
                'is_spike': bool,
                'alert_message': str or None
            }
        """
        # 현재 거래량
        current_data = await self.get_current_volume(symbol)
        
        if current_data is None:
            return {'error': 'Failed to fetch volume'}
        
        current_volume = current_data['volume']
        
        # 히스토리 초기화
        if symbol not in self.volume_history:
            self.volume_history[symbol] = deque(maxlen=24)  # 24시간 데이터
        
        # 평균 거래량 계산
        if len(self.volume_history[symbol]) < 5:
            # 데이터 부족 시 현재 데이터만 저장
            self.volume_history[symbol].append(current_volume)
            return {
                'symbol': symbol,
                'current_volume': current_volume,
                'is_spike': False,
                'message': 'Collecting baseline data'
            }
        
        avg_volume = sum(self.volume_history[symbol]) / len(self.volume_history[symbol])
        spike_ratio = current_volume / avg_volume
        
        # 급증 여부
        is_spike = spike_ratio >= self.spike_threshold
        
        result = {
            'symbol': symbol,
            'current_volume': round(current_volume, 2),
            'avg_volume': round(avg_volume, 2),
            'spike_ratio': round(spike_ratio, 2),
            'is_spike': is_spike,
            'alert_message': self._generate_volume_alert(symbol, spike_ratio) if is_spike else None,
            'timestamp': datetime.now().isoformat()
        }
        
        # 히스토리 업데이트
        self.volume_history[symbol].append(current_volume)
        
        if is_spike:
            logger.warning(f"🚨 거래량 급증: {symbol} - {spike_ratio:.1f}배")
        
        return result
    
    def _generate_volume_alert(self, symbol: str, spike_ratio: float) -> str:
        """거래량 알림 메시지 생성"""
        return f"⚡ {symbol} 거래량 {spike_ratio:.1f}배 급증! 큰 움직임 예상 - 주의 요망"


class WhaleTransferTracker:
    """
    고래 움직임 추적
    대량 전송 감지 (실제로는 blockchain explorer API 필요)
    """
    
    def __init__(self, whale_threshold: float = 100.0):
        """
        Args:
            whale_threshold: 고래 기준 (BTC 기준, 100 BTC 이상)
        """
        self.whale_threshold = whale_threshold
        self.recent_transfers = deque(maxlen=50)
        
    async def get_large_transfers(self, symbol: str = 'BTC') -> List[Dict]:
        """
        대량 전송 조회
        
        Note: 실제로는 Whale Alert API나 blockchain explorer 사용
        현재는 시뮬레이션
        """
        # 실제 구현 시:
        # - Whale Alert API
        # - Blockchain.com API
        # - Etherscan API (ETH)
        
        # 시뮬레이션 데이터 (실제로는 API 호출)
        simulated_transfers = []
        
        # 여기에 실제 API 호출 로직 추가
        # Example:
        # async with aiohttp.ClientSession() as session:
        #     url = "https://api.whale-alert.io/v1/transactions"
        #     async with session.get(url, params={'api_key': 'xxx'}) as response:
        #         data = await response.json()
        
        return simulated_transfers
    
    async def detect_whale_movements(self, symbol: str = 'BTC') -> Dict:
        """
        고래 움직임 감지
        
        Returns:
            {
                'symbol': str,
                'whale_transfers_24h': int,
                'total_amount': float,
                'to_exchanges': int,
                'from_exchanges': int,
                'net_flow': float,
                'alert': bool,
                'alert_message': str
            }
        """
        transfers = await self.get_large_transfers(symbol)
        
        # 분석
        to_exchange = 0
        from_exchange = 0
        total_amount = 0
        
        for transfer in transfers:
            amount = transfer.get('amount', 0)
            total_amount += amount
            
            if transfer.get('to_type') == 'exchange':
                to_exchange += 1
            if transfer.get('from_type') == 'exchange':
                from_exchange += 1
        
        net_flow = from_exchange - to_exchange
        
        # 알림 조건: 거래소로 대량 유입 (매도 압력)
        alert = to_exchange >= 3  # 3건 이상
        
        result = {
            'symbol': symbol,
            'whale_transfers_24h': len(transfers),
            'total_amount': round(total_amount, 2),
            'to_exchanges': to_exchange,
            'from_exchanges': from_exchange,
            'net_flow': net_flow,
            'alert': alert,
            'alert_message': self._generate_whale_alert(symbol, to_exchange, total_amount) if alert else None,
            'timestamp': datetime.now().isoformat()
        }
        
        if alert:
            logger.warning(f"🐋 고래 알림: {symbol} - 거래소로 {to_exchange}건 전송")
        
        return result
    
    def _generate_whale_alert(self, symbol: str, count: int, amount: float) -> str:
        """고래 알림 메시지 생성"""
        return f"🐋 고래 {count}건 거래소 입금 ({amount:.1f} {symbol})! 대량 매도 압력 예상"


class QuickWinsAggregator:
    """
    Quick Wins 통합 모니터링
    """
    
    def __init__(self):
        self.kimchi_monitor = KimchiPremiumMonitor(alert_threshold=2.0)
        self.volume_detector = VolumeAnomalyDetector(spike_threshold=3.0)
        self.whale_tracker = WhaleTransferTracker(whale_threshold=100.0)
        
    async def get_all_alerts(self, symbols: List[str] = ['BTC', 'ETH']) -> Dict:
        """
        모든 Quick Wins 알림 통합 조회
        
        Returns:
            {
                'kimchi_premium': {...},
                'volume_spikes': [...],
                'whale_movements': [...],
                'total_alerts': int,
                'timestamp': str
            }
        """
        alerts = {
            'kimchi_premium': {},
            'volume_spikes': [],
            'whale_movements': [],
            'total_alerts': 0,
            'timestamp': datetime.now().isoformat()
        }
        
        # 1. 김치 프리미엄 (BTC만)
        kimchi_result = await self.kimchi_monitor.calculate_premium('BTC')
        alerts['kimchi_premium'] = kimchi_result
        if kimchi_result.get('alert'):
            alerts['total_alerts'] += 1
        
        # 2. 거래량 급증 (모든 심볼)
        for symbol in symbols:
            symbol_usdt = f"{symbol}USDT"
            volume_result = await self.volume_detector.detect_volume_spike(symbol_usdt)
            if volume_result.get('is_spike'):
                alerts['volume_spikes'].append(volume_result)
                alerts['total_alerts'] += 1
        
        # 3. 고래 움직임 (모든 심볼)
        for symbol in symbols:
            whale_result = await self.whale_tracker.detect_whale_movements(symbol)
            if whale_result.get('alert'):
                alerts['whale_movements'].append(whale_result)
                alerts['total_alerts'] += 1
        
        return alerts
    
    async def continuous_monitoring(self, symbols: List[str] = ['BTC', 'ETH'], interval: int = 60):
        """
        지속적 모니터링 (백그라운드)
        
        Args:
            symbols: 모니터링할 심볼 리스트
            interval: 체크 간격 (초)
        """
        logger.info(f"🚀 Quick Wins 모니터링 시작: {symbols}, 간격: {interval}초")
        
        while True:
            try:
                alerts = await self.get_all_alerts(symbols)
                
                if alerts['total_alerts'] > 0:
                    logger.info(f"⚠️ 총 {alerts['total_alerts']}개 알림 발생")
                    
                    # 김치 프리미엄
                    if alerts['kimchi_premium'].get('alert'):
                        logger.warning(alerts['kimchi_premium']['alert_message'])
                    
                    # 거래량 급증
                    for spike in alerts['volume_spikes']:
                        logger.warning(spike['alert_message'])
                    
                    # 고래 움직임
                    for whale in alerts['whale_movements']:
                        logger.warning(whale['alert_message'])
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(interval)
