"""
Quick Wins API Endpoints
- 김치 프리미엄
- 거래량 급증
- 고래 움직임
"""
from fastapi import APIRouter, HTTPException
from typing import List
from loguru import logger

from ai.quick_wins import QuickWinsAggregator

router = APIRouter()

# Global instance
quick_wins = QuickWinsAggregator()


@router.get("/quick-wins/all")
async def get_all_quick_wins(symbols: str = "BTC,ETH"):
    """
    모든 Quick Wins 알림 조회
    
    Args:
        symbols: 쉼표로 구분된 심볼 리스트 (예: "BTC,ETH,SOL")
    
    Returns:
        {
            'kimchi_premium': {...},
            'volume_spikes': [...],
            'whale_movements': [...],
            'total_alerts': int
        }
    """
    try:
        symbol_list = [s.strip() for s in symbols.split(',')]
        alerts = await quick_wins.get_all_alerts(symbol_list)
        return alerts
    except Exception as e:
        logger.error(f"Quick wins fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quick-wins/kimchi-premium")
async def get_kimchi_premium(symbol: str = "BTC"):
    """
    김치 프리미엄 조회
    
    Args:
        symbol: 심볼 (BTC, ETH 등)
    
    Returns:
        {
            'binance_price': float,
            'upbit_price_usd': float,
            'premium_pct': float,
            'alert': bool
        }
    """
    try:
        result = await quick_wins.kimchi_monitor.calculate_premium(symbol)
        return result
    except Exception as e:
        logger.error(f"Kimchi premium fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quick-wins/kimchi-premium/trend")
async def get_kimchi_premium_trend():
    """
    김치 프리미엄 추세 조회
    
    Returns:
        {
            'trend': 'INCREASING' | 'DECREASING' | 'STABLE',
            'avg_premium': float,
            'max_premium': float,
            'min_premium': float
        }
    """
    try:
        trend = quick_wins.kimchi_monitor.get_premium_trend()
        return trend
    except Exception as e:
        logger.error(f"Premium trend fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quick-wins/volume-spike")
async def get_volume_spike(symbol: str = "BTCUSDT"):
    """
    거래량 급증 감지
    
    Args:
        symbol: Binance 심볼 (예: BTCUSDT, ETHUSDT)
    
    Returns:
        {
            'current_volume': float,
            'avg_volume': float,
            'spike_ratio': float,
            'is_spike': bool
        }
    """
    try:
        result = await quick_wins.volume_detector.detect_volume_spike(symbol)
        return result
    except Exception as e:
        logger.error(f"Volume spike detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quick-wins/whale-movements")
async def get_whale_movements(symbol: str = "BTC"):
    """
    고래 움직임 추적
    
    Args:
        symbol: 심볼 (BTC, ETH 등)
    
    Returns:
        {
            'whale_transfers_24h': int,
            'to_exchanges': int,
            'from_exchanges': int,
            'net_flow': int,
            'alert': bool
        }
    """
    try:
        result = await quick_wins.whale_tracker.detect_whale_movements(symbol)
        return result
    except Exception as e:
        logger.error(f"Whale movement tracking failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
