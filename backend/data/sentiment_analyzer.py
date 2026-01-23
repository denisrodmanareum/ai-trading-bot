"""
Sentiment Analyzer
소셜 미디어 및 뉴스 감정 분석으로 시장 심리 측정
"""
import asyncio
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from collections import deque
import os
import re


class TwitterSentimentAnalyzer:
    """
    트위터 감정 분석
    (실제로는 Twitter API v2 필요)
    """
    
    def __init__(self, bearer_token: Optional[str] = None):
        self.bearer_token = bearer_token or os.getenv('TWITTER_BEARER_TOKEN', '')
        self.base_url = "https://api.twitter.com/2"
        
    async def analyze_hashtag_sentiment(self, hashtag: str = "Bitcoin") -> Dict:
        """
        해시태그 감정 분석
        
        Returns:
            {
                'positive': int,
                'negative': int,
                'neutral': int,
                'sentiment_score': float (-1 ~ 1),
                'tweet_volume': int,
                'trending': bool
            }
        """
        # 실제 구현 시 Twitter API 사용
        # 현재는 시뮬레이션
        return self._simulate_twitter_sentiment(hashtag)
    
    async def get_influencer_sentiment(self) -> Dict:
        """
        영향력있는 계정들의 감정 분석
        
        예: @elonmusk, @michael_saylor, @VitalikButerin 등
        """
        influencers = [
            'elonmusk', 'michael_saylor', 'VitalikButerin',
            'CZ_Binance', 'brian_armstrong'
        ]
        
        # 실제로는 각 인플루언서의 최근 트윗 분석
        return self._simulate_influencer_sentiment()
    
    def _simulate_twitter_sentiment(self, hashtag: str) -> Dict:
        """시뮬레이션 데이터"""
        import random
        
        total = random.randint(10000, 50000)
        positive = int(total * random.uniform(0.3, 0.6))
        negative = int(total * random.uniform(0.1, 0.3))
        neutral = total - positive - negative
        
        sentiment_score = (positive - negative) / total
        
        return {
            'hashtag': hashtag,
            'positive': positive,
            'negative': negative,
            'neutral': neutral,
            'sentiment_score': round(sentiment_score, 3),
            'tweet_volume': total,
            'trending': total > 30000,
            'timestamp': datetime.now().isoformat(),
            'simulated': True
        }
    
    def _simulate_influencer_sentiment(self) -> Dict:
        """시뮬레이션 데이터"""
        import random
        
        sentiments = ['BULLISH', 'BEARISH', 'NEUTRAL']
        return {
            'overall_sentiment': random.choice(sentiments),
            'bullish_count': random.randint(2, 4),
            'bearish_count': random.randint(0, 2),
            'neutral_count': random.randint(1, 3),
            'confidence': round(random.uniform(0.6, 0.9), 2),
            'timestamp': datetime.now().isoformat(),
            'simulated': True
        }


class RedditSentimentAnalyzer:
    """
    Reddit 감정 분석
    r/cryptocurrency, r/Bitcoin 등
    """
    
    def __init__(self):
        self.subreddits = ['cryptocurrency', 'Bitcoin', 'ethtrader']
        
    async def analyze_subreddit_sentiment(self, subreddit: str = 'cryptocurrency') -> Dict:
        """
        서브레딧 감정 분석
        
        Returns:
            {
                'sentiment_score': float,
                'post_volume': int,
                'comment_volume': int,
                'top_topics': list
            }
        """
        # Reddit API 사용 (실제로는 PRAW 라이브러리)
        return self._simulate_reddit_sentiment(subreddit)
    
    async def get_fear_greed_index(self) -> Dict:
        """
        Fear & Greed Index
        
        0-20:   Extreme Fear
        20-40:  Fear
        40-60:  Neutral
        60-80:  Greed
        80-100: Extreme Greed
        """
        # Alternative.me API
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://api.alternative.me/fng/"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'data' in data and len(data['data']) > 0:
                            latest = data['data'][0]
                            value = int(latest['value'])
                            
                            if value <= 20:
                                classification = 'EXTREME_FEAR'
                            elif value <= 40:
                                classification = 'FEAR'
                            elif value <= 60:
                                classification = 'NEUTRAL'
                            elif value <= 80:
                                classification = 'GREED'
                            else:
                                classification = 'EXTREME_GREED'
                            
                            return {
                                'value': value,
                                'classification': classification,
                                'value_classification': latest['value_classification'],
                                'timestamp': latest['timestamp'],
                                'signal': 'BUY' if value <= 30 else 'SELL' if value >= 70 else 'HOLD'
                            }
        except Exception as e:
            logger.error(f"Fear & Greed Index fetch failed: {e}")
        
        return self._simulate_fear_greed_index()
    
    def _simulate_reddit_sentiment(self, subreddit: str) -> Dict:
        """시뮬레이션 데이터"""
        import random
        
        sentiment_score = random.uniform(-0.3, 0.7)  # 일반적으로 긍정적
        
        return {
            'subreddit': subreddit,
            'sentiment_score': round(sentiment_score, 3),
            'post_volume': random.randint(500, 2000),
            'comment_volume': random.randint(5000, 20000),
            'top_topics': ['Bitcoin', 'ETF', 'Regulation', 'Price', 'Technical Analysis'],
            'timestamp': datetime.now().isoformat(),
            'simulated': True
        }
    
    def _simulate_fear_greed_index(self) -> Dict:
        """시뮬레이션 데이터"""
        import random
        
        value = random.randint(20, 80)
        
        if value <= 20:
            classification = 'EXTREME_FEAR'
        elif value <= 40:
            classification = 'FEAR'
        elif value <= 60:
            classification = 'NEUTRAL'
        elif value <= 80:
            classification = 'GREED'
        else:
            classification = 'EXTREME_GREED'
        
        return {
            'value': value,
            'classification': classification,
            'timestamp': int(datetime.now().timestamp()),
            'signal': 'BUY' if value <= 30 else 'SELL' if value >= 70 else 'HOLD',
            'simulated': True
        }


class NewsSentimentAnalyzer:
    """
    뉴스 헤드라인 감정 분석
    """
    
    def __init__(self):
        self.keywords_bullish = [
            'adoption', 'bullish', 'surge', 'rally', 'breakthrough',
            'approve', 'green', 'gain', 'rise', 'positive', 'etf approved'
        ]
        self.keywords_bearish = [
            'crash', 'plunge', 'bearish', 'decline', 'fall', 'reject',
            'ban', 'regulation', 'hack', 'scam', 'negative'
        ]
        
    async def analyze_recent_news(self, query: str = 'Bitcoin') -> Dict:
        """
        최근 뉴스 헤드라인 분석
        
        Returns:
            {
                'headlines': list,
                'sentiment_score': float,
                'bullish_count': int,
                'bearish_count': int,
                'major_events': list
            }
        """
        # 실제로는 News API 또는 RSS 피드 사용
        return self._simulate_news_sentiment(query)
    
    def _analyze_headline_sentiment(self, headline: str) -> float:
        """
        헤드라인 감정 분석 (간단한 키워드 기반)
        
        Returns:
            -1.0 (매우 부정) ~ 1.0 (매우 긍정)
        """
        headline_lower = headline.lower()
        
        bullish_score = sum(1 for keyword in self.keywords_bullish if keyword in headline_lower)
        bearish_score = sum(1 for keyword in self.keywords_bearish if keyword in headline_lower)
        
        if bullish_score + bearish_score == 0:
            return 0.0
        
        sentiment = (bullish_score - bearish_score) / (bullish_score + bearish_score)
        return sentiment
    
    def _simulate_news_sentiment(self, query: str) -> Dict:
        """시뮬레이션 데이터"""
        import random
        
        sample_headlines = [
            f"{query} ETF Approval Boosting Market Confidence",
            f"{query} Price Consolidates After Recent Rally",
            f"Regulatory Concerns Weigh on {query} Market",
            f"Major Institution Adopts {query} for Treasury",
            f"{query} Network Activity Reaches New High",
            f"Analyst Predicts {query} Breakthrough to New ATH",
            f"Market Volatility Increases Amid {query} Uncertainty"
        ]
        
        headlines = random.sample(sample_headlines, 5)
        sentiments = [self._analyze_headline_sentiment(h) for h in headlines]
        
        avg_sentiment = sum(sentiments) / len(sentiments)
        bullish_count = sum(1 for s in sentiments if s > 0.3)
        bearish_count = sum(1 for s in sentiments if s < -0.3)
        
        return {
            'query': query,
            'headlines': headlines[:5],
            'sentiment_score': round(avg_sentiment, 3),
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'neutral_count': len(headlines) - bullish_count - bearish_count,
            'major_events': ['ETF Decision', 'Regulatory Update'] if random.random() > 0.5 else [],
            'timestamp': datetime.now().isoformat(),
            'simulated': True
        }


class MarketSentimentAggregator:
    """
    통합 시장 감정 분석기
    """
    
    def __init__(self):
        self.twitter = TwitterSentimentAnalyzer()
        self.reddit = RedditSentimentAnalyzer()
        self.news = NewsSentimentAnalyzer()
        self.sentiment_history = deque(maxlen=100)
        
    async def get_comprehensive_sentiment(self, asset: str = 'Bitcoin') -> Dict:
        """
        종합 시장 감정 분석
        
        Returns:
            {
                'overall_sentiment': str (BULLISH/BEARISH/NEUTRAL),
                'sentiment_index': int (0-100),
                'confidence': float,
                'sources': {...}
            }
        """
        try:
            # 병렬로 모든 감정 데이터 수집
            twitter_sentiment, influencer_sentiment, reddit_sentiment, fear_greed, news_sentiment = await asyncio.gather(
                self.twitter.analyze_hashtag_sentiment(asset),
                self.twitter.get_influencer_sentiment(),
                self.reddit.analyze_subreddit_sentiment(),
                self.reddit.get_fear_greed_index(),
                self.news.analyze_recent_news(asset)
            )
            
            # 종합 감정 지수 계산 (0-100)
            sentiment_index = self._calculate_sentiment_index({
                'twitter': twitter_sentiment,
                'influencer': influencer_sentiment,
                'reddit': reddit_sentiment,
                'fear_greed': fear_greed,
                'news': news_sentiment
            })
            
            # 전체 감정 분류
            if sentiment_index >= 70:
                overall_sentiment = 'BULLISH'
            elif sentiment_index <= 30:
                overall_sentiment = 'BEARISH'
            else:
                overall_sentiment = 'NEUTRAL'
            
            # 신뢰도 계산
            confidence = self._calculate_confidence(sentiment_index)
            
            result = {
                'asset': asset,
                'overall_sentiment': overall_sentiment,
                'sentiment_index': sentiment_index,
                'confidence': confidence,
                'trading_signal': self._generate_trading_signal(sentiment_index, fear_greed),
                'sources': {
                    'twitter': {
                        'sentiment_score': twitter_sentiment['sentiment_score'],
                        'volume': twitter_sentiment['tweet_volume'],
                        'trending': twitter_sentiment['trending']
                    },
                    'influencer': {
                        'sentiment': influencer_sentiment['overall_sentiment'],
                        'confidence': influencer_sentiment['confidence']
                    },
                    'reddit': {
                        'sentiment_score': reddit_sentiment['sentiment_score'],
                        'volume': reddit_sentiment['post_volume']
                    },
                    'fear_greed': {
                        'value': fear_greed['value'],
                        'classification': fear_greed['classification'],
                        'signal': fear_greed['signal']
                    },
                    'news': {
                        'sentiment_score': news_sentiment['sentiment_score'],
                        'bullish_count': news_sentiment['bullish_count'],
                        'bearish_count': news_sentiment['bearish_count']
                    }
                },
                'timestamp': datetime.now().isoformat()
            }
            
            # 히스토리 저장
            self.sentiment_history.append(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Comprehensive sentiment analysis failed: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _calculate_sentiment_index(self, sources: Dict) -> int:
        """
        모든 소스를 종합하여 0-100 감정 지수 계산
        """
        scores = []
        weights = []
        
        # Twitter (가중치: 0.25)
        twitter_normalized = (sources['twitter']['sentiment_score'] + 1) * 50  # -1~1 → 0~100
        scores.append(twitter_normalized)
        weights.append(0.25)
        
        # Influencer (가중치: 0.20)
        influencer_map = {'BULLISH': 75, 'NEUTRAL': 50, 'BEARISH': 25}
        scores.append(influencer_map[sources['influencer']['overall_sentiment']])
        weights.append(0.20)
        
        # Reddit (가중치: 0.15)
        reddit_normalized = (sources['reddit']['sentiment_score'] + 1) * 50
        scores.append(reddit_normalized)
        weights.append(0.15)
        
        # Fear & Greed (가중치: 0.25)
        scores.append(sources['fear_greed']['value'])
        weights.append(0.25)
        
        # News (가중치: 0.15)
        news_normalized = (sources['news']['sentiment_score'] + 1) * 50
        scores.append(news_normalized)
        weights.append(0.15)
        
        # 가중 평균
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        
        return int(round(weighted_sum))
    
    def _calculate_confidence(self, sentiment_index: int) -> float:
        """
        감정 지수에 따른 신뢰도 계산
        
        극단적일수록 신뢰도 높음
        중립적일수록 신뢰도 낮음
        """
        distance_from_neutral = abs(sentiment_index - 50)
        confidence = 0.5 + (distance_from_neutral / 50) * 0.5
        return round(confidence, 2)
    
    def _generate_trading_signal(self, sentiment_index: int, fear_greed: Dict) -> Dict:
        """
        감정 지수 기반 거래 시그널 생성
        """
        # 역발상 전략 (Contrarian)
        if sentiment_index >= 80 or fear_greed['value'] >= 80:
            signal = 'SELL'
            reason = 'Extreme Greed - Market overheated'
        elif sentiment_index <= 20 or fear_greed['value'] <= 20:
            signal = 'BUY'
            reason = 'Extreme Fear - Buying opportunity'
        elif sentiment_index >= 65:
            signal = 'TAKE_PROFIT'
            reason = 'High greed - Consider taking profits'
        elif sentiment_index <= 35:
            signal = 'ACCUMULATE'
            reason = 'Fear present - Good accumulation zone'
        else:
            signal = 'HOLD'
            reason = 'Neutral sentiment - No strong signal'
        
        return {
            'signal': signal,
            'reason': reason,
            'strategy': 'CONTRARIAN'  # 역발상
        }
    
    def get_sentiment_trend(self, lookback: int = 10) -> Dict:
        """
        감정 추세 분석
        """
        if len(self.sentiment_history) < lookback:
            return {'trend': 'INSUFFICIENT_DATA'}
        
        recent = list(self.sentiment_history)[-lookback:]
        indices = [s['sentiment_index'] for s in recent]
        
        if indices[-1] > indices[0] + 10:
            trend = 'IMPROVING'
        elif indices[-1] < indices[0] - 10:
            trend = 'DECLINING'
        else:
            trend = 'STABLE'
        
        avg_index = sum(indices) / len(indices)
        
        return {
            'trend': trend,
            'avg_sentiment_index': round(avg_index, 1),
            'current_index': indices[-1],
            'change': indices[-1] - indices[0],
            'lookback_periods': lookback
        }
