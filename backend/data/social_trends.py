"""
Social Media Trends Analyzer
소셜 미디어 트렌드: Twitter, Reddit 등
"""
from typing import Dict, List, Optional
import aiohttp
from loguru import logger
from datetime import datetime
import random


class SocialTrendsAnalyzer:
    """
    소셜 미디어 트렌드 분석
    - Twitter/X API (현재 제한적)
    - Reddit API
    - 감성 분석
    """
    
    def __init__(self):
        # Reddit API
        self.reddit_base = "https://www.reddit.com/r/cryptocurrency"
        
        # Mock trending topics for demo
        self.crypto_topics = [
            'Bitcoin', 'Ethereum', 'Solana', 'BNB', 'XRP',
            'Cardano', 'Dogecoin', 'Avalanche', 'Polygon', 'Chainlink'
        ]
    
    async def get_social_trends(self) -> List[Dict]:
        """
        소셜 미디어 트렌드 가져오기
        
        Returns:
            List of trending topics with sentiment
        """
        try:
            # Fetch Reddit trends
            reddit_trends = await self._fetch_reddit_trends()
            
            # Generate Twitter-like trends (mock for now)
            twitter_trends = self._generate_twitter_trends()
            
            # Combine and sort by mentions
            all_trends = reddit_trends + twitter_trends
            all_trends.sort(key=lambda x: x['mentions'], reverse=True)
            
            return all_trends[:10]
            
        except Exception as e:
            logger.error(f"Failed to get social trends: {e}")
            return self._get_mock_social_trends()
    
    async def _fetch_reddit_trends(self) -> List[Dict]:
        """Reddit r/cryptocurrency 트렌드"""
        try:
            async with aiohttp.ClientSession() as session:
                # Fetch hot posts
                url = f"{self.reddit_base}/hot.json"
                headers = {'User-Agent': 'CryptoTradingBot/1.0'}
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        posts = data.get('data', {}).get('children', [])
                        
                        trends = []
                        topic_counts = {}
                        
                        for post in posts[:50]:  # Top 50 posts
                            post_data = post.get('data', {})
                            title = post_data.get('title', '').lower()
                            score = post_data.get('score', 0)
                            
                            # Extract crypto mentions
                            for topic in self.crypto_topics:
                                if topic.lower() in title:
                                    if topic not in topic_counts:
                                        topic_counts[topic] = {
                                            'mentions': 0,
                                            'total_score': 0,
                                            'posts': []
                                        }
                                    topic_counts[topic]['mentions'] += 1
                                    topic_counts[topic]['total_score'] += score
                                    topic_counts[topic]['posts'].append({
                                        'title': post_data.get('title', ''),
                                        'score': score,
                                        'url': f"https://reddit.com{post_data.get('permalink', '')}"
                                    })
                        
                        # Convert to trends list
                        for topic, data in topic_counts.items():
                            avg_score = data['total_score'] / data['mentions'] if data['mentions'] > 0 else 0
                            
                            # Determine sentiment from score
                            if avg_score > 1000:
                                sentiment = 'Very Bullish'
                                sentiment_emoji = '🚀'
                                sentiment_score = 85
                            elif avg_score > 500:
                                sentiment = 'Bullish'
                                sentiment_emoji = '📈'
                                sentiment_score = 70
                            elif avg_score > 100:
                                sentiment = 'Positive'
                                sentiment_emoji = '😊'
                                sentiment_score = 60
                            else:
                                sentiment = 'Neutral'
                                sentiment_emoji = '😐'
                                sentiment_score = 50
                            
                            trends.append({
                                'topic': topic,
                                'platform': 'Reddit',
                                'mentions': data['mentions'],
                                'sentiment': sentiment,
                                'sentiment_emoji': sentiment_emoji,
                                'sentiment_score': sentiment_score,
                                'avg_score': int(avg_score),
                                'top_posts': data['posts'][:3],
                                'change_24h': random.randint(-50, 100)  # Mock change
                            })
                        
                        return trends
        except Exception as e:
            logger.error(f"Failed to fetch Reddit trends: {e}")
        
        return []
    
    def _generate_twitter_trends(self) -> List[Dict]:
        """Generate mock Twitter trends"""
        trends = []
        
        for topic in random.sample(self.crypto_topics, 5):
            mentions = random.randint(50000, 500000)
            sentiment_score = random.randint(30, 90)
            
            if sentiment_score > 70:
                sentiment = 'Bullish'
                sentiment_emoji = '📈'
            elif sentiment_score > 50:
                sentiment = 'Positive'
                sentiment_emoji = '😊'
            else:
                sentiment = 'Neutral'
                sentiment_emoji = '😐'
            
            trends.append({
                'topic': topic,
                'platform': 'Twitter',
                'mentions': mentions,
                'sentiment': sentiment,
                'sentiment_emoji': sentiment_emoji,
                'sentiment_score': sentiment_score,
                'change_24h': random.randint(-30, 80),
                'hashtags': [f'#{topic}', '#Crypto', '#Trading']
            })
        
        return trends
    
    def _get_mock_social_trends(self) -> List[Dict]:
        """Fallback mock social trends"""
        trends = []
        
        for i, topic in enumerate(self.crypto_topics[:10]):
            mentions = random.randint(50000, 500000)
            sentiment_score = random.randint(40, 90)
            
            if sentiment_score > 70:
                sentiment = 'Bullish'
                sentiment_emoji = '📈'
            elif sentiment_score > 50:
                sentiment = 'Positive'
                sentiment_emoji = '😊'
            else:
                sentiment = 'Neutral'
                sentiment_emoji = '😐'
            
            trends.append({
                'topic': topic,
                'platform': random.choice(['Twitter', 'Reddit']),
                'mentions': mentions,
                'sentiment': sentiment,
                'sentiment_emoji': sentiment_emoji,
                'sentiment_score': sentiment_score,
                'change_24h': random.randint(-30, 80),
                'rank': i + 1
            })
        
        return trends
    
    async def get_topic_sentiment(self, topic: str) -> Dict:
        """
        특정 토픽의 감성 분석
        
        Args:
            topic: 토픽 (e.g., 'Bitcoin', 'Ethereum')
        
        Returns:
            Sentiment analysis for the topic
        """
        trends = await self.get_social_trends()
        
        for trend in trends:
            if trend['topic'].lower() == topic.lower():
                return {
                    'topic': topic,
                    'sentiment': trend['sentiment'],
                    'sentiment_score': trend['sentiment_score'],
                    'mentions_24h': trend['mentions'],
                    'change_24h': trend['change_24h'],
                    'platforms': {
                        'twitter': random.randint(10000, 100000),
                        'reddit': random.randint(100, 1000)
                    },
                    'updated_at': datetime.now().isoformat()
                }
        
        # Default if not found
        return {
            'topic': topic,
            'sentiment': 'Neutral',
            'sentiment_score': 50,
            'mentions_24h': 0,
            'change_24h': 0,
            'platforms': {'twitter': 0, 'reddit': 0},
            'updated_at': datetime.now().isoformat()
        }


# Global instance
social_trends_analyzer = SocialTrendsAnalyzer()
