"""
Crypto VIX (Volatility Index)
Market-wide volatility indicator for crypto markets
"""
import numpy as np
from typing import Dict
from loguru import logger


class CryptoVIX:
    """
    암호화폐 시장 변동성 지수 (VIX 스타일)
    - BTC 기반 변동성 계산
    - 0~100 점수
    - 리스크 파라미터 자동 조정
    """
    
    def __init__(self, exchange_client):
        self.exchange_client = exchange_client
        self.binance_client = exchange_client
        self.current_vix = 0.0
        self.vix_history = []
    
    async def calculate_vix(self) -> float:
        """
        Crypto VIX 계산
        BTC ATR 기반 변동성 지수
        
        Returns:
            VIX score (0~100)
        """
        try:
            # BTC 1시간 차트 조회
            df = await self.exchange_client.get_klines('BTCUSDT', '1h', 100)
            
            if df is None or len(df) < 20:
                return self.current_vix  # 이전 값 유지
            
            # ATR 계산 (이미 있으면 사용)
            if 'atr' not in df.columns:
                from ai.features import add_technical_indicators
                df = add_technical_indicators(df)
            
            # 현재 가격과 ATR
            current_price = df['close'].iloc[-1]
            atr = df['atr'].iloc[-1]
            
            # ATR 기반 변동성 (%)
            volatility_pct = (atr / current_price) * 100
            
            # VIX 점수로 정규화 (0~100)
            # 0.5% = 10점
            # 1.0% = 20점
            # 2.5% = 50점
            # 5.0% = 100점
            vix_score = min(100, volatility_pct * 20)
            
            self.current_vix = vix_score
            self.vix_history.append(vix_score)
            
            # 최근 100개만 유지
            if len(self.vix_history) > 100:
                self.vix_history = self.vix_history[-100:]
            
            logger.debug(f"📊 Crypto VIX: {vix_score:.1f} (ATR: {volatility_pct:.2f}%)")
            
            return vix_score
            
        except Exception as e:
            logger.error(f"VIX calculation failed: {e}")
            return self.current_vix
    
    def get_risk_adjustment(self, vix: float = None) -> Dict:
        """
        VIX 기반 리스크 파라미터 조정
        
        Args:
            vix: VIX 점수 (None이면 현재 값 사용)
            
        Returns:
            {
                'max_leverage': int,
                'max_exposure': float,
                'position_size_multiplier': float,
                'regime': str
            }
        """
        if vix is None:
            vix = self.current_vix
        
        if vix < 20:  # 낮은 변동성
            return {
                'max_leverage': 10,
                'max_exposure': 0.30,
                'position_size_multiplier': 1.2,
                'stop_distance_multiplier': 0.8,  # 좁은 손절
                'regime': 'LOW_VOLATILITY'
            }
        elif vix < 40:  # 중간 변동성
            return {
                'max_leverage': 5,
                'max_exposure': 0.26,
                'position_size_multiplier': 1.0,
                'stop_distance_multiplier': 1.0,  # 기본
                'regime': 'NORMAL_VOLATILITY'
            }
        elif vix < 60:  # 높은 변동성
            return {
                'max_leverage': 3,
                'max_exposure': 0.20,
                'position_size_multiplier': 0.7,
                'stop_distance_multiplier': 1.3,  # 넓은 손절
                'regime': 'HIGH_VOLATILITY'
            }
        else:  # 극도로 높은 변동성
            return {
                'max_leverage': 2,
                'max_exposure': 0.15,
                'position_size_multiplier': 0.5,
                'stop_distance_multiplier': 1.5,  # 매우 넓은 손절
                'regime': 'EXTREME_VOLATILITY'
            }
    
    def get_vix_stats(self) -> Dict:
        """VIX 통계"""
        if not self.vix_history:
            return {
                'current': 0.0,
                'avg': 0.0,
                'min': 0.0,
                'max': 0.0
            }
        
        return {
            'current': self.current_vix,
            'avg': np.mean(self.vix_history),
            'min': np.min(self.vix_history),
            'max': np.max(self.vix_history),
            'std': np.std(self.vix_history),
            'trend': 'increasing' if self.current_vix > np.mean(self.vix_history) else 'decreasing'
        }
