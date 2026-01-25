"""
Performance Monitor
Monitors trading performance and triggers alerts/retraining
"""
import numpy as np
from typing import Dict, List
from loguru import logger
from datetime import datetime, timedelta
from app.services.notifications import notification_manager, NotificationType


class PerformanceMonitor:
    """
    실시간 성과 모니터링 시스템
    - 성과 저하 감지
    - 자동 알림
    - 재학습 트리거
    """
    
    def __init__(self, exchange_client, auto_trading_service=None):
        self.exchange_client = exchange_client
        self.auto_trading_service = auto_trading_service
        
        # 베이스라인 (목표 성과)
        self.baseline = {
            'win_rate': 0.45,
            'avg_profit_pct': 1.5,
            'sharpe_ratio': 1.5,
            'max_drawdown': -8.0
        }
        
        # 경고 임계값 (베이스라인 대비 %)
        self.alert_thresholds = {
            'win_rate': 0.80,  # 80% 미만이면 경고
            'avg_profit': 0.70,
            'sharpe': 0.70,
            'drawdown': 1.5  # 150% 초과하면 경고
        }
        
        self.last_check_time = None
        self.check_interval = timedelta(hours=6)  # 6시간마다 체크
    
    async def check_performance_degradation(self, days: int = 7) -> Dict:
        """
        성과 저하 감지
        
        Args:
            days: 최근 N일 데이터 분석
            
        Returns:
            {
                'status': str,  # 'ok', 'warning', 'critical'
                'alerts': List[str],
                'metrics': Dict,
                'needs_retraining': bool
            }
        """
        try:
            # 최근 거래 조회
            trades = await self.get_recent_trades(days=days)
            
            if len(trades) < 10:
                return {
                    'status': 'insufficient_data',
                    'alerts': [f"Not enough trades ({len(trades)}) for analysis"],
                    'metrics': {},
                    'needs_retraining': False
                }
            
            # 메트릭 계산
            metrics = self.calculate_metrics(trades)
            
            # 알림 생성
            alerts = []
            status = 'ok'
            
            # 1. 승률 체크
            if metrics['win_rate'] < self.baseline['win_rate'] * self.alert_thresholds['win_rate']:
                alerts.append(
                    f"⚠️ Win rate dropped: {metrics['win_rate']:.1%} "
                    f"< {self.baseline['win_rate'] * self.alert_thresholds['win_rate']:.1%}"
                )
                status = 'warning'
            
            # 2. 평균 수익 체크
            if metrics['avg_profit_pct'] < self.baseline['avg_profit_pct'] * self.alert_thresholds['avg_profit']:
                alerts.append(
                    f"📉 Avg profit low: {metrics['avg_profit_pct']:.2f}% "
                    f"< {self.baseline['avg_profit_pct'] * self.alert_thresholds['avg_profit']:.2f}%"
                )
                status = 'warning'
            
            # 3. Sharpe ratio 체크
            if 'sharpe_ratio' in metrics and metrics['sharpe_ratio'] < self.baseline['sharpe_ratio'] * self.alert_thresholds['sharpe']:
                alerts.append(
                    f"📊 Sharpe ratio low: {metrics['sharpe_ratio']:.2f} "
                    f"< {self.baseline['sharpe_ratio'] * self.alert_thresholds['sharpe']:.2f}"
                )
                status = 'warning'
            
            # 4. Drawdown 체크
            if metrics['max_drawdown'] < self.baseline['max_drawdown'] * self.alert_thresholds['drawdown']:
                alerts.append(
                    f"🚨 Max drawdown exceeded: {metrics['max_drawdown']:.1f}% "
                    f"< {self.baseline['max_drawdown'] * self.alert_thresholds['drawdown']:.1f}%"
                )
                status = 'critical'
            
            # 재학습 필요 여부
            needs_retraining = status == 'critical' or len(alerts) >= 2
            
            # 알림 발송
            if alerts:
                await self.send_performance_alert(status, alerts, metrics)
            
            return {
                'status': status,
                'alerts': alerts,
                'metrics': metrics,
                'needs_retraining': needs_retraining
            }
            
        except Exception as e:
            logger.error(f"Performance check failed: {e}")
            return {
                'status': 'error',
                'alerts': [f"Performance check failed: {str(e)}"],
                'metrics': {},
                'needs_retraining': False
            }
    
    async def get_recent_trades(self, days: int = 7) -> List[Dict]:
        """최근 거래 조회"""
        try:
            from app.database import SessionLocal
            from app.models import Trade
            from sqlalchemy import select
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            async with SessionLocal() as db:
                result = await db.execute(
                    select(Trade).where(
                        Trade.entry_time >= cutoff_date,
                        Trade.status == 'CLOSED'
                    ).order_by(Trade.entry_time.desc())
                )
                trades = result.scalars().all()
                
                return [
                    {
                        'symbol': t.symbol,
                        'pnl': t.pnl or 0.0,
                        'roi': t.roi or 0.0,
                        'entry_time': t.entry_time,
                        'exit_time': t.exit_time
                    }
                    for t in trades
                ]
        except Exception as e:
            logger.error(f"Failed to get recent trades: {e}")
            return []
    
    def calculate_metrics(self, trades: List[Dict]) -> Dict:
        """메트릭 계산"""
        if not trades:
            return {}
        
        # 승률
        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] < 0]
        win_rate = len(wins) / len(trades)
        
        # 평균 수익/손실
        avg_win = np.mean([t['pnl'] for t in wins]) if wins else 0
        avg_loss = np.mean([t['pnl'] for t in losses]) if losses else 0
        avg_profit_pct = np.mean([t['roi'] for t in trades])
        
        # 총 수익
        total_pnl = sum([t['pnl'] for t in trades])
        
        # Sharpe ratio (간단 버전)
        returns = [t['roi'] for t in trades]
        if len(returns) > 1:
            sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Max drawdown
        cumulative = np.cumsum([t['pnl'] for t in trades])
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - running_max
        max_drawdown = np.min(drawdown)
        
        return {
            'total_trades': len(trades),
            'win_rate': win_rate,
            'wins': len(wins),
            'losses': len(losses),
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_profit_pct': avg_profit_pct,
            'total_pnl': total_pnl,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0
        }
    
    async def send_performance_alert(self, status: str, alerts: List[str], metrics: Dict):
        """성과 알림 발송"""
        try:
            title = f"⚠️ Performance {status.upper()}"
            
            message = "\n".join(alerts)
            message += "\n\n📊 **Current Metrics:**\n"
            message += f"Win Rate: {metrics.get('win_rate', 0):.1%}\n"
            message += f"Avg Profit: {metrics.get('avg_profit_pct', 0):.2f}%\n"
            message += f"Total PnL: {metrics.get('total_pnl', 0):.2f} USDT\n"
            message += f"Sharpe: {metrics.get('sharpe_ratio', 0):.2f}\n"
            
            await notification_manager.send(
                NotificationType.PRICE_ALERT,
                title,
                message,
                channels=["telegram"]
            )
            
        except Exception as e:
            logger.error(f"Failed to send performance alert: {e}")
    
    async def trigger_retraining(self):
        """자동 재학습 트리거"""
        try:
            logger.warning("🔄 Performance degradation detected - triggering retraining")
            
            # 자동 재학습 (있으면)
            if self.auto_trading_service:
                # 재학습 로직은 별도로 구현 필요
                logger.info("Retraining will be implemented...")
            
            # 알림
            await notification_manager.send(
                NotificationType.PRICE_ALERT,
                "🤖 Auto Retraining Triggered",
                "Performance degradation detected. Starting model retraining...",
                channels=["telegram"]
            )
            
        except Exception as e:
            logger.error(f"Failed to trigger retraining: {e}")
