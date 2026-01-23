"""
Crypto News Aggregator & Sentiment Analyzer
실시간 암호화폐 뉴스 수집 및 감성 분석
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import aiohttp
import asyncio
from loguru import logger
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import feedparser
from bs4 import BeautifulSoup


class CryptoNewsAggregator:
    """
    암호화폐 뉴스 수집기
    - CoinDesk, CoinTelegraph, CryptoNews 등
    - RSS 피드 기반
    """
    
    def __init__(self):
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        
        # RSS Feeds
        self.news_sources = {
            "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "CoinTelegraph": "https://cointelegraph.com/rss",
            "Decrypt": "https://decrypt.co/feed",
            "CryptoNews": "https://cryptonews.com/news/feed/",
            "Bitcoin.com": "https://news.bitcoin.com/feed/"
        }
        
        # Crypto keywords for filtering
        self.crypto_keywords = [
            'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'cryptocurrency',
            'blockchain', 'defi', 'nft', 'altcoin', 'trading', 'binance',
            'coinbase', 'sec', 'regulation', 'adoption', 'mining', 'whale',
            'bull', 'bear', 'market', 'price', 'rally', 'crash', 'pump'
        ]
    
    async def fetch_latest_news(self, limit: int = 30, hours_ago: int = 24) -> List[Dict]:
        """
        최신 뉴스 수집
        
        Args:
            limit: 최대 뉴스 개수
            hours_ago: 몇 시간 전까지 뉴스 수집
        
        Returns:
            List of news articles with sentiment analysis
        """
        all_news = []
        cutoff_time = datetime.now() - timedelta(hours=hours_ago)
        
        for source_name, feed_url in self.news_sources.items():
            try:
                news = await self._fetch_rss_feed(source_name, feed_url, cutoff_time)
                all_news.extend(news)
            except Exception as e:
                logger.error(f"Failed to fetch from {source_name}: {e}")
        
        # Sort by published time (newest first)
        all_news.sort(key=lambda x: x['published_at'], reverse=True)
        
        # Limit results
        return all_news[:limit]
    
    async def _fetch_rss_feed(self, source: str, url: str, cutoff_time: datetime) -> List[Dict]:
        """RSS 피드에서 뉴스 추출"""
        try:
            # Parse RSS feed
            feed = feedparser.parse(url)
            news_list = []
            
            for entry in feed.entries:
                try:
                    # Parse published time
                    if hasattr(entry, 'published_parsed'):
                        pub_time = datetime(*entry.published_parsed[:6])
                    else:
                        pub_time = datetime.now()
                    
                    # Skip old news
                    if pub_time < cutoff_time:
                        continue
                    
                    # Extract title and description
                    title = entry.get('title', '')
                    description = entry.get('summary', '')
                    
                    # Clean HTML tags
                    if description:
                        soup = BeautifulSoup(description, 'html.parser')
                        description = soup.get_text()[:300]
                    
                    # Analyze sentiment
                    sentiment = self._analyze_sentiment(title, description)
                    
                    # Calculate importance
                    importance = self._calculate_importance(title, description)
                    
                    news_item = {
                        'source': source,
                        'title': title,
                        'description': description,
                        'url': entry.get('link', ''),
                        'published_at': pub_time.isoformat(),
                        'sentiment': sentiment,
                        'importance': importance,
                        'tags': self._extract_tags(title, description)
                    }
                    
                    news_list.append(news_item)
                    
                except Exception as e:
                    logger.error(f"Error parsing entry from {source}: {e}")
                    continue
            
            return news_list
            
        except Exception as e:
            logger.error(f"Failed to parse RSS from {source}: {e}")
            return []
    
    def _analyze_sentiment(self, title: str, description: str) -> Dict:
        """
        감성 분석 수행
        
        Returns:
            {
                'label': 'bullish'/'bearish'/'neutral',
                'score': 0-100,
                'confidence': 0-1
            }
        """
        text = f"{title}. {description}".lower()
        
        # VADER sentiment analysis
        scores = self.sentiment_analyzer.polarity_scores(text)
        compound = scores['compound']
        
        # Additional bullish/bearish keyword detection
        bullish_keywords = [
            'surge', 'rally', 'pump', 'moon', 'bullish', 'gain', 'rise',
            'up', 'high', 'all-time', 'adoption', 'breakout', 'buy'
        ]
        bearish_keywords = [
            'crash', 'dump', 'bearish', 'fall', 'down', 'low', 'sell',
            'plunge', 'decline', 'regulation', 'ban', 'hack', 'scam'
        ]
        
        bullish_count = sum(1 for keyword in bullish_keywords if keyword in text)
        bearish_count = sum(1 for keyword in bearish_keywords if keyword in text)
        
        # Adjust compound score with keywords
        keyword_adjustment = (bullish_count - bearish_count) * 0.1
        final_score = compound + keyword_adjustment
        
        # Determine label
        if final_score > 0.2:
            label = 'bullish'
            emoji = '📈'
        elif final_score < -0.2:
            label = 'bearish'
            emoji = '📉'
        else:
            label = 'neutral'
            emoji = '📊'
        
        # Normalize score to 0-100
        score = int((final_score + 1) * 50)
        score = max(0, min(100, score))
        
        return {
            'label': label,
            'emoji': emoji,
            'score': score,
            'confidence': abs(final_score),
            'details': {
                'positive': scores['pos'],
                'negative': scores['neg'],
                'neutral': scores['neu']
            }
        }
    
    def _calculate_importance(self, title: str, description: str) -> str:
        """
        뉴스 중요도 계산
        
        Returns:
            'hot', 'important', 'normal'
        """
        text = f"{title} {description}".lower()
        
        # Hot keywords (매우 중요)
        hot_keywords = [
            'sec', 'etf', 'regulation', 'ban', 'hack', 'crash', 'all-time high',
            'breaking', 'urgent', 'alert', 'major', 'significant', 'record'
        ]
        
        # Important keywords
        important_keywords = [
            'bitcoin', 'ethereum', 'adoption', 'institutional', 'whale',
            'exchange', 'launch', 'partnership', 'upgrade', 'halving'
        ]
        
        # Check hot keywords
        for keyword in hot_keywords:
            if keyword in text:
                return 'hot'
        
        # Check important keywords
        for keyword in important_keywords:
            if keyword in text:
                return 'important'
        
        return 'normal'
    
    def _extract_tags(self, title: str, description: str) -> List[str]:
        """Extract relevant crypto tags from news"""
        text = f"{title} {description}".lower()
        tags = []
        
        crypto_symbols = {
            'btc': 'Bitcoin',
            'bitcoin': 'Bitcoin',
            'eth': 'Ethereum',
            'ethereum': 'Ethereum',
            'sol': 'Solana',
            'solana': 'Solana',
            'bnb': 'BNB',
            'xrp': 'Ripple',
            'ripple': 'Ripple',
            'ada': 'Cardano',
            'cardano': 'Cardano',
            'doge': 'Dogecoin',
            'dogecoin': 'Dogecoin'
        }
        
        for symbol, name in crypto_symbols.items():
            if symbol in text:
                if name not in tags:
                    tags.append(name)
        
        # Add category tags
        if any(word in text for word in ['regulation', 'sec', 'law', 'legal']):
            tags.append('Regulation')
        if any(word in text for word in ['etf', 'institutional', 'adoption']):
            tags.append('Institutional')
        if any(word in text for word in ['defi', 'protocol', 'smart contract']):
            tags.append('DeFi')
        if any(word in text for word in ['nft', 'metaverse', 'gaming']):
            tags.append('NFT')
        
        return tags[:5]  # Limit to 5 tags
    
    async def get_trending_topics(self, hours_ago: int = 24) -> List[Dict]:
        """
        트렌딩 토픽 분석
        
        Returns:
            List of trending topics with mention count
        """
        news = await self.fetch_latest_news(limit=100, hours_ago=hours_ago)
        
        # Count tag occurrences
        tag_counts = {}
        for article in news:
            for tag in article['tags']:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Sort by count
        trending = [
            {'topic': tag, 'mentions': count}
            for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        return trending[:10]


# Global instance
crypto_news_aggregator = CryptoNewsAggregator()
