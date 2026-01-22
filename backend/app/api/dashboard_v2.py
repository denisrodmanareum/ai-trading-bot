"""
Dashboard V2 API - Information Dashboard
종합 정보 대시보드 API 엔드포인트
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from loguru import logger

from data.crypto_news import crypto_news_aggregator
from data.market_data import market_data_aggregator
from data.onchain_data import onchain_data_analyzer
from data.social_trends import social_trends_analyzer

router = APIRouter()


@router.get("/v2/overview")
async def get_dashboard_overview():
    """
    대시보드 전체 개요
    모든 정보를 한번에 가져오기
    """
    try:
        # Fetch all data concurrently
        import asyncio
        
        news, market, whale, funding, social = await asyncio.gather(
            crypto_news_aggregator.fetch_latest_news(limit=10),
            market_data_aggregator.get_market_overview(),
            onchain_data_analyzer.get_whale_activities(hours_ago=24),
            onchain_data_analyzer.get_funding_rates(),
            social_trends_analyzer.get_social_trends(),
            return_exceptions=True
        )
        
        return {
            "status": "success",
            "news": news if not isinstance(news, Exception) else [],
            "market": market if not isinstance(market, Exception) else {},
            "whale_activities": whale if not isinstance(whale, Exception) else [],
            "funding_rates": funding if not isinstance(funding, Exception) else [],
            "social_trends": social if not isinstance(social, Exception) else []
        }
    except Exception as e:
        logger.error(f"Failed to fetch dashboard overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v2/news")
async def get_crypto_news(limit: int = 20, hours_ago: int = 24):
    """
    실시간 암호화폐 뉴스
    
    Args:
        limit: 최대 뉴스 개수
        hours_ago: 몇 시간 전까지
    """
    try:
        news = await crypto_news_aggregator.fetch_latest_news(
            limit=limit,
            hours_ago=hours_ago
        )
        return {"status": "success", "news": news, "count": len(news)}
    except Exception as e:
        logger.error(f"Failed to fetch news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v2/news/trending")
async def get_trending_topics(hours_ago: int = 24):
    """트렌딩 뉴스 토픽"""
    try:
        trending = await crypto_news_aggregator.get_trending_topics(hours_ago=hours_ago)
        return {"status": "success", "trending": trending}
    except Exception as e:
        logger.error(f"Failed to fetch trending topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v2/market")
async def get_market_overview():
    """
    시장 전체 개요
    - Total Market Cap
    - Fear & Greed Index
    - Trending Coins
    - Top Gainers/Losers
    """
    try:
        market = await market_data_aggregator.get_market_overview()
        return {"status": "success", "market": market}
    except Exception as e:
        logger.error(f"Failed to fetch market overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v2/market/coin/{symbol}")
async def get_coin_market_data(symbol: str):
    """특정 코인의 상세 시장 데이터"""
    try:
        data = await market_data_aggregator.get_coin_market_data(symbol)
        if not data:
            raise HTTPException(status_code=404, detail="Coin not found")
        return {"status": "success", "data": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch coin data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v2/onchain/whale")
async def get_whale_activities(hours_ago: int = 24, min_usd: int = 1000000):
    """
    고래 거래 활동
    
    Args:
        hours_ago: 몇 시간 전까지
        min_usd: 최소 거래 금액 (USD)
    """
    try:
        whale = await onchain_data_analyzer.get_whale_activities(
            hours_ago=hours_ago,
            min_usd=min_usd
        )
        return {"status": "success", "whale_activities": whale, "count": len(whale)}
    except Exception as e:
        logger.error(f"Failed to fetch whale activities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v2/onchain/netflow/{symbol}")
async def get_exchange_netflow(symbol: str):
    """
    거래소 유입/유출 (Netflow)
    
    Args:
        symbol: 코인 심볼 (e.g., BTC, ETH)
    """
    try:
        netflow = await onchain_data_analyzer.get_exchange_netflow(symbol)
        return {"status": "success", "netflow": netflow}
    except Exception as e:
        logger.error(f"Failed to fetch netflow for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v2/onchain/funding")
async def get_funding_rates():
    """펀딩 레이트 (Binance Futures)"""
    try:
        funding = await onchain_data_analyzer.get_funding_rates()
        return {"status": "success", "funding_rates": funding}
    except Exception as e:
        logger.error(f"Failed to fetch funding rates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v2/onchain/open-interest/{symbol}")
async def get_open_interest(symbol: str = "BTCUSDT"):
    """Open Interest"""
    try:
        oi = await onchain_data_analyzer.get_open_interest(symbol)
        return {"status": "success", "open_interest": oi}
    except Exception as e:
        logger.error(f"Failed to fetch open interest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v2/onchain/long-short-ratio/{symbol}")
async def get_long_short_ratio(symbol: str = "BTCUSDT"):
    """Long/Short Ratio"""
    try:
        ratio = await onchain_data_analyzer.get_long_short_ratio(symbol)
        return {"status": "success", "long_short_ratio": ratio}
    except Exception as e:
        logger.error(f"Failed to fetch long/short ratio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v2/social/trends")
async def get_social_trends():
    """
    소셜 미디어 트렌드
    - Twitter/X
    - Reddit
    """
    try:
        trends = await social_trends_analyzer.get_social_trends()
        return {"status": "success", "trends": trends}
    except Exception as e:
        logger.error(f"Failed to fetch social trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v2/social/sentiment/{topic}")
async def get_topic_sentiment(topic: str):
    """
    특정 토픽의 감성 분석
    
    Args:
        topic: 토픽 (e.g., Bitcoin, Ethereum)
    """
    try:
        sentiment = await social_trends_analyzer.get_topic_sentiment(topic)
        return {"status": "success", "sentiment": sentiment}
    except Exception as e:
        logger.error(f"Failed to fetch sentiment for {topic}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v2/ai/signals")
async def get_ai_trading_signals():
    """
    AI 트레이딩 신호
    - 매수/매도 추천
    - 신호 강도
    - 예상 수익률
    """
    try:
        # This would integrate with actual AI model
        # For now, return mock data
        import random
        
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']
        signals = []
        
        for symbol in symbols:
            signal_strength = random.randint(50, 95)
            
            if signal_strength > 80:
                action = 'STRONG BUY'
                emoji = '🚀'
                risk = 'Medium'
            elif signal_strength > 70:
                action = 'BUY'
                emoji = '📈'
                risk = 'Low'
            elif signal_strength > 60:
                action = 'HOLD'
                emoji = '😐'
                risk = 'Low'
            else:
                action = 'NEUTRAL'
                emoji = '⚠️'
                risk = 'High'
            
            signals.append({
                'symbol': symbol,
                'action': action,
                'emoji': emoji,
                'signal_strength': signal_strength,
                'risk_level': risk,
                'entry_price': random.uniform(100, 50000),
                'target_price': random.uniform(110, 55000),
                'stop_loss': random.uniform(90, 45000),
                'expected_return': random.uniform(5, 15),
                'timeframe': random.choice(['4h', '1d', '1w']),
                'indicators': {
                    'rsi': random.randint(30, 70),
                    'macd': random.choice(['Bullish Cross', 'Bearish Cross', 'Neutral']),
                    'trend': random.choice(['Uptrend', 'Downtrend', 'Sideways']),
                    'volume': random.choice(['Above Average', 'Below Average', 'Normal'])
                }
            })
        
        # Sort by signal strength
        signals.sort(key=lambda x: x['signal_strength'], reverse=True)
        
        return {"status": "success", "signals": signals}
    except Exception as e:
        logger.error(f"Failed to generate AI signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))
