"""
AI Daily Review and Self-Learning System
Analyzes daily performance and continuously improves
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
import json
from pathlib import Path


class DailyReviewAnalyzer:
    """
    Performs daily review of AI trading performance
    Identifies patterns, mistakes, and improvement opportunities
    """
    
    def __init__(self, data_dir: str = "data/reviews"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.review_history = []
        self.performance_metrics = {
            'daily_pnl': [],
            'win_rate': [],
            'avg_profit': [],
            'avg_loss': [],
            'max_drawdown': [],
            'sharpe_ratio': [],
            'total_trades': []
        }
    
    def analyze_daily_performance(
        self,
        trades: List[Dict],
        date: Optional[datetime] = None
    ) -> Dict:
        """
        Analyze performance for a specific day
        
        Args:
            trades: List of trade dictionaries
            date: Date to analyze (defaults to yesterday)
        
        Returns:
            {
                'date': str,
                'total_trades': int,
                'win_rate': float,
                'total_pnl': float,
                'best_trade': dict,
                'worst_trade': dict,
                'patterns': list,
                'mistakes': list,
                'recommendations': list
            }
        """
        if date is None:
            date = datetime.now() - timedelta(days=1)
        
        date_str = date.strftime('%Y-%m-%d')
        
        if not trades:
            logger.warning(f"No trades found for {date_str}")
            return self._empty_review(date_str)
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(trades)
        
        # Calculate metrics
        total_trades = len(df)
        winning_trades = df[df['pnl'] > 0]
        losing_trades = df[df['pnl'] < 0]
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        total_pnl = df['pnl'].sum()
        avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0
        
        # Find best and worst trades
        best_trade = df.loc[df['pnl'].idxmax()].to_dict() if total_trades > 0 else {}
        worst_trade = df.loc[df['pnl'].idxmin()].to_dict() if total_trades > 0 else {}
        
        # Identify patterns
        patterns = self._identify_patterns(df)
        
        # Identify mistakes
        mistakes = self._identify_mistakes(df)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(df, patterns, mistakes)
        
        review = {
            'date': date_str,
            'total_trades': total_trades,
            'win_rate': round(win_rate, 3),
            'total_pnl': round(total_pnl, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'patterns': patterns,
            'mistakes': mistakes,
            'recommendations': recommendations,
            'timestamp': datetime.now().isoformat()
        }
        
        # Save review
        self._save_review(review)
        
        # Update performance metrics
        self._update_metrics(review)
        
        logger.info(f"Daily review completed for {date_str}: {total_trades} trades, PnL: {total_pnl:.2f}, WR: {win_rate:.1%}")
        
        return review
    
    def _empty_review(self, date_str: str) -> Dict:
        """Return empty review structure"""
        return {
            'date': date_str,
            'total_trades': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'best_trade': {},
            'worst_trade': {},
            'patterns': [],
            'mistakes': [],
            'recommendations': ['거래가 실행되지 않았습니다 - 전략 파라미터 조정을 고려하세요'],
            'timestamp': datetime.now().isoformat()
        }
    
    def _identify_patterns(self, df: pd.DataFrame) -> List[str]:
        """
        Identify successful/unsuccessful patterns
        """
        patterns = []
        
        try:
            # Pattern 1: Time of day analysis
            if 'timestamp' in df.columns:
                # Use format='ISO8601' to handle various ISO8601 formats (with or without microseconds)
                df['hour'] = pd.to_datetime(df['timestamp'], format='ISO8601', errors='coerce').dt.hour
                hourly_pnl = df.groupby('hour')['pnl'].sum()
                
                best_hour = hourly_pnl.idxmax()
                worst_hour = hourly_pnl.idxmin()
                
                if hourly_pnl[best_hour] > 0:
                    patterns.append(f"가장 수익성 높은 시간: {best_hour}:00 (수익: {hourly_pnl[best_hour]:.2f})")
                if hourly_pnl[worst_hour] < 0:
                    patterns.append(f"가장 낮은 성과 시간: {worst_hour}:00 (손실: {hourly_pnl[worst_hour]:.2f})")
            
            # Pattern 2: Trade direction analysis
            if 'side' in df.columns:
                long_pnl = df[df['side'] == 'LONG']['pnl'].sum()
                short_pnl = df[df['side'] == 'SHORT']['pnl'].sum()
                
                if long_pnl > short_pnl and long_pnl > 0:
                    patterns.append(f"롱 포지션이 더 우수했습니다 (롱: {long_pnl:.2f} vs 숏: {short_pnl:.2f})")
                elif short_pnl > long_pnl and short_pnl > 0:
                    patterns.append(f"숏 포지션이 더 우수했습니다 (숏: {short_pnl:.2f} vs 롱: {long_pnl:.2f})")
            
            # Pattern 3: Position size analysis
            if 'quantity' in df.columns and 'pnl' in df.columns:
                df['size_category'] = pd.cut(df['quantity'], bins=3, labels=['Small', 'Medium', 'Large'])
                size_pnl = df.groupby('size_category')['pnl'].mean()
                
                best_size = size_pnl.idxmax()
                patterns.append(f"최고 성과 포지션 크기: {best_size} (평균 수익: {size_pnl[best_size]:.2f})")
            
            # Pattern 4: Holding duration
            if 'entry_time' in df.columns and 'exit_time' in df.columns:
                # Use format='ISO8601' to handle various ISO8601 formats
                exit_times = pd.to_datetime(df['exit_time'], format='ISO8601', errors='coerce')
                entry_times = pd.to_datetime(df['entry_time'], format='ISO8601', errors='coerce')
                df['duration'] = (exit_times - entry_times).dt.total_seconds() / 60
                
                # Correlate duration with PnL
                correlation = df['duration'].corr(df['pnl'])
                if abs(correlation) > 0.3:
                    if correlation > 0:
                        patterns.append(f"긴 보유 시간이 더 수익성 높은 경향 (상관계수: {correlation:.2f})")
                    else:
                        patterns.append(f"짧은 보유 시간이 더 수익성 높은 경향 (상관계수: {correlation:.2f})")
            
        except Exception as e:
            logger.error(f"Pattern identification failed: {e}")
        
        return patterns
    
    def _identify_mistakes(self, df: pd.DataFrame) -> List[str]:
        """
        Identify common mistakes and anti-patterns
        """
        mistakes = []
        
        try:
            # Mistake 1: Frequent losing trades in a row
            df = df.sort_values('timestamp') if 'timestamp' in df.columns else df
            df['is_loss'] = df['pnl'] < 0
            
            max_consecutive_losses = 0
            current_losses = 0
            
            for loss in df['is_loss']:
                if loss:
                    current_losses += 1
                    max_consecutive_losses = max(max_consecutive_losses, current_losses)
                else:
                    current_losses = 0
            
            if max_consecutive_losses >= 3:
                mistakes.append(f"{max_consecutive_losses}번 연속 손실 거래 발생 - 2회 손실 후 일시 중지를 고려하세요")
            
            # Mistake 2: Large single loss
            if 'pnl' in df.columns:
                max_loss = df['pnl'].min()
                total_pnl = df['pnl'].sum()
                
                if max_loss < 0 and abs(max_loss) > abs(total_pnl) * 0.5:
                    mistakes.append(f"단일 큰 손실 ({max_loss:.2f})이 일일 이익의 50% 이상을 상쇄했습니다")
            
            # Mistake 3: Overtrading
            total_trades = len(df)
            if total_trades > 50:  # More than ~2 trades per hour (assuming 24h)
                mistakes.append(f"고빈도 거래 감지됨 ({total_trades}건) - 과도한 거래 가능성")
            
            # Mistake 4: Poor risk/reward ratio
            if len(df[df['pnl'] > 0]) > 0 and len(df[df['pnl'] < 0]) > 0:
                avg_win = df[df['pnl'] > 0]['pnl'].mean()
                avg_loss = abs(df[df['pnl'] < 0]['pnl'].mean())
                
                rr_ratio = avg_win / avg_loss if avg_loss > 0 else 0
                
                if rr_ratio < 1.0:
                    mistakes.append(f"낮은 위험/보상 비율: {rr_ratio:.2f} (평균 수익: {avg_win:.2f}, 평균 손실: {avg_loss:.2f})")
            
        except Exception as e:
            logger.error(f"Mistake identification failed: {e}")
        
        return mistakes
    
    def _generate_recommendations(
        self,
        df: pd.DataFrame,
        patterns: List[str],
        mistakes: List[str]
    ) -> List[str]:
        """
        Generate actionable recommendations
        """
        recommendations = []
        
        try:
            # Based on win rate
            win_rate = len(df[df['pnl'] > 0]) / len(df) if len(df) > 0 else 0
            
            if win_rate < 0.4:
                recommendations.append("승률이 낮습니다 (<40%) - 진입 기준을 강화하거나 AI 신뢰도 임계값 조정을 고려하세요")
            elif win_rate > 0.7:
                recommendations.append("승률이 높습니다 (>70%) - 포지션 크기 증가 또는 더 많은 거래를 고려하세요")
            
            # Based on mistakes
            if any('consecutive' in m for m in mistakes):
                recommendations.append("회로 차단기 구현: 2-3회 연속 손실 후 거래 일시 중지")
            
            if any('large loss' in m for m in mistakes):
                recommendations.append("더 엄격한 손절매 및 포지션 크기 제한 구현")
            
            if any('overtrading' in m for m in mistakes):
                recommendations.append("거래 빈도 감소 - 최소 신호 강도 요구사항 증가")
            
            # Based on patterns
            if any('LONG' in p and 'outperformed' in p for p in patterns):
                recommendations.append("현재 시장 상황에서 롱 신호 가중치 증가를 고려하세요")
            
            if any('SHORT' in p and 'outperformed' in p for p in patterns):
                recommendations.append("현재 시장 상황에서 숏 신호 가중치 증가를 고려하세요")
            
            # General recommendations
            if len(df) == 0:
                recommendations.append("거래가 실행되지 않음 - 전략 파라미터 및 신호 생성 검토")
            
        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
        
        return recommendations if recommendations else ["현재 전략 모니터링 계속"]
    
    def _save_review(self, review: Dict):
        """Save review to file"""
        try:
            filename = self.data_dir / f"review_{review['date']}.json"
            with open(filename, 'w') as f:
                json.dump(review, f, indent=2, default=str)
            
            logger.info(f"Review saved to {filename}")
            
        except Exception as e:
            logger.error(f"Failed to save review: {e}")
    
    def _update_metrics(self, review: Dict):
        """Update performance metrics history"""
        self.performance_metrics['daily_pnl'].append(review['total_pnl'])
        self.performance_metrics['win_rate'].append(review['win_rate'])
        self.performance_metrics['total_trades'].append(review['total_trades'])
        
        # Keep last 30 days only
        for key in self.performance_metrics:
            if len(self.performance_metrics[key]) > 30:
                self.performance_metrics[key] = self.performance_metrics[key][-30:]
    
    def get_weekly_summary(self) -> Dict:
        """
        Generate weekly performance summary
        """
        try:
            # Load last 7 days of reviews
            reviews = []
            for i in range(7):
                date = datetime.now() - timedelta(days=i)
                date_str = date.strftime('%Y-%m-%d')
                filename = self.data_dir / f"review_{date_str}.json"
                
                if filename.exists():
                    with open(filename, 'r') as f:
                        reviews.append(json.load(f))
            
            if not reviews:
                return {'message': 'No reviews available'}
            
            # Aggregate metrics
            total_trades = sum(r['total_trades'] for r in reviews)
            total_pnl = sum(r['total_pnl'] for r in reviews)
            avg_win_rate = np.mean([r['win_rate'] for r in reviews])
            
            # Best and worst days
            best_day = max(reviews, key=lambda x: x['total_pnl'])
            worst_day = min(reviews, key=lambda x: x['total_pnl'])
            
            return {
                'period': '7 days',
                'total_trades': total_trades,
                'total_pnl': round(total_pnl, 2),
                'avg_win_rate': round(avg_win_rate, 3),
                'best_day': {'date': best_day['date'], 'pnl': best_day['total_pnl']},
                'worst_day': {'date': worst_day['date'], 'pnl': worst_day['total_pnl']},
                'num_reviews': len(reviews)
            }
            
        except Exception as e:
            logger.error(f"Weekly summary failed: {e}")
            return {'error': str(e)}
    
    def suggest_ai_improvements(self) -> Dict:
        """
        Suggest specific AI model improvements based on performance analysis
        """
        suggestions = {
            'reward_function': [],
            'training_data': [],
            'hyperparameters': [],
            'features': []
        }
        
        try:
            # Analyze recent metrics
            if len(self.performance_metrics['win_rate']) < 5:
                return {'message': 'Need more data (at least 5 days)'}
            
            recent_wr = np.mean(self.performance_metrics['win_rate'][-5:])
            recent_pnl = np.mean(self.performance_metrics['daily_pnl'][-5:])
            
            # Suggestions based on win rate
            if recent_wr < 0.45:
                suggestions['reward_function'].append("낮은 신뢰도 거래에 대한 페널티 추가 고려")
                suggestions['training_data'].append("Add more samples from current market regime")
                suggestions['hyperparameters'].append("탐색 증가 (높은 엡실론 값)")
            
            # Suggestions based on PnL trend
            if recent_pnl < 0:
                suggestions['reward_function'].append("위험 조정 수익률에 대한 가중치 증가")
                suggestions['features'].append("Add market regime awareness")
                suggestions['hyperparameters'].append("안정성을 위한 학습률 감소")
            
            # Variance analysis
            wr_variance = np.var(self.performance_metrics['win_rate'][-10:])
            if wr_variance > 0.05:  # High variance
                suggestions['training_data'].append("안정성을 위한 학습 데이터셋 크기 증가")
                suggestions['hyperparameters'].append("Add regularization")
            
        except Exception as e:
            logger.error(f"AI improvement suggestions failed: {e}")
        
        return suggestions
