"""
Advanced Data API Endpoints
- On-Chain Data
- Sentiment Analysis
"""
from fastapi import APIRouter, HTTPException
from loguru import logger

from data.onchain_analyzer import OnChainAnalyzer
from data.sentiment_analyzer import MarketSentimentAggregator

router = APIRouter()

# Global instances
onchain_analyzer = OnChainAnalyzer()
sentiment_aggregator = MarketSentimentAggregator()


@router.get("/advanced-data/onchain")
async def get_onchain_data(asset: str = "BTC"):
    """
    온체인 데이터 조회
    
    Args:
        asset: BTC, ETH 등
    
    Returns:
        {
            'exchange_flows': {...},
            'whale_activity': {...},
            'network_activity': {...},
            'miner_behavior': {...},
            'overall_signal': 'BULLISH' | 'BEARISH' | 'NEUTRAL',
            'confidence': float
        }
    """
    try:
        data = await onchain_analyzer.get_comprehensive_onchain_data(asset)
        return data
    except Exception as e:
        logger.error(f"On-chain data fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advanced-data/onchain/trend")
async def get_onchain_trend(lookback: int = 10):
    """
    온체인 데이터 추세
    """
    try:
        trend = onchain_analyzer.get_onchain_trend(lookback)
        return trend
    except Exception as e:
        logger.error(f"On-chain trend fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advanced-data/sentiment")
async def get_sentiment(asset: str = "Bitcoin"):
    """
    종합 시장 감정 분석
    
    Returns:
        {
            'overall_sentiment': 'BULLISH' | 'BEARISH' | 'NEUTRAL',
            'sentiment_index': int (0-100),
            'confidence': float,
            'trading_signal': {...},
            'sources': {
                'twitter': {...},
                'reddit': {...},
                'fear_greed': {...},
                'news': {...}
            }
        }
    """
    try:
        sentiment = await sentiment_aggregator.get_comprehensive_sentiment(asset)
        return sentiment
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advanced-data/sentiment/trend")
async def get_sentiment_trend(lookback: int = 10):
    """
    감정 추세 분석
    """
    try:
        trend = sentiment_aggregator.get_sentiment_trend(lookback)
        return trend
    except Exception as e:
        logger.error(f"Sentiment trend fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advanced-data/fear-greed")
async def get_fear_greed():
    """
    Fear & Greed Index만 조회
    
    Returns:
        {
            'value': int (0-100),
            'classification': str,
            'signal': 'BUY' | 'SELL' | 'HOLD'
        }
    """
    try:
        fear_greed = await sentiment_aggregator.reddit.get_fear_greed_index()
        return fear_greed
    except Exception as e:
        logger.error(f"Fear & Greed Index fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advanced-data/combined")
async def get_combined_analysis(asset: str = "BTC"):
    """
    온체인 + 감정 분석 통합
    
    Returns:
        {
            'onchain': {...},
            'sentiment': {...},
            'combined_signal': str,
            'confidence': float,
            'recommendation': str
        }
    """
    try:
        # 병렬로 데이터 수집
        import asyncio
        onchain, sentiment = await asyncio.gather(
            onchain_analyzer.get_comprehensive_onchain_data(asset),
            sentiment_aggregator.get_comprehensive_sentiment(asset if asset == 'BTC' else 'Bitcoin')
        )
        
        # 통합 시그널 생성
        combined_signal, confidence, recommendation = _generate_combined_signal(onchain, sentiment)
        
        return {
            'asset': asset,
            'onchain': onchain,
            'sentiment': sentiment,
            'combined_signal': combined_signal,
            'combined_confidence': confidence,
            'recommendation': recommendation,
            'timestamp': onchain.get('timestamp')
        }
        
    except Exception as e:
        logger.error(f"Combined analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _generate_combined_signal(onchain: dict, sentiment: dict) -> tuple:
    """
    온체인 + 감정을 종합한 시그널 생성
    
    Returns:
        (signal: str, confidence: float, recommendation: str)
    """
    # 온체인 시그널
    onchain_signal = onchain.get('overall_signal', 'NEUTRAL')
    onchain_confidence = onchain.get('confidence', 0.5)
    
    # 감정 시그널
    sentiment_signal = sentiment.get('overall_sentiment', 'NEUTRAL')
    sentiment_confidence = sentiment.get('confidence', 0.5)
    
    # 두 시그널이 일치하는가?
    if onchain_signal == sentiment_signal:
        # 일치: 강한 시그널
        combined_signal = onchain_signal
        confidence = (onchain_confidence + sentiment_confidence) / 2
        
        if combined_signal == 'BULLISH':
            recommendation = "강력 매수 시그널 - 온체인 + 감정 모두 긍정적"
        elif combined_signal == 'BEARISH':
            recommendation = "강력 매도 시그널 - 온체인 + 감정 모두 부정적"
        else:
            recommendation = "관망 - 온체인 + 감정 모두 중립"
    
    else:
        # 불일치: 약한 시그널
        if onchain_signal == 'BULLISH' and sentiment_signal == 'BEARISH':
            combined_signal = 'MIXED'
            confidence = 0.5
            recommendation = "혼조 - 온체인은 긍정, 감정은 부정 (조심스러운 접근)"
        
        elif onchain_signal == 'BEARISH' and sentiment_signal == 'BULLISH':
            combined_signal = 'MIXED'
            confidence = 0.5
            recommendation = "혼조 - 온체인은 부정, 감정은 긍정 (단기 상승 가능하나 주의)"
        
        else:
            # 하나가 NEUTRAL
            if onchain_signal == 'NEUTRAL':
                combined_signal = sentiment_signal
                confidence = sentiment_confidence * 0.7
            else:
                combined_signal = onchain_signal
                confidence = onchain_confidence * 0.7
            
            recommendation = f"약한 {combined_signal} 시그널 - 한 쪽만 명확"
    
    return combined_signal, round(confidence, 2), recommendation
