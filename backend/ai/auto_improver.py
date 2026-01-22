"""
Auto-Improvement System
매일 자정 자동 재학습 및 성과 분석
"""
import asyncio
from datetime import datetime, time
from loguru import logger
from ai.trainer import train_agent
from ai.agent import TradingAgent
from trading.binance_client import BinanceClient


class AutoImprover:
    """AI 자동 개선 시스템"""
    
    def __init__(self, binance_client: BinanceClient):
        self.binance_client = binance_client
        self.enabled = False
        self.last_training = None
        self.performance_history = []
        
    async def start(self):
        """자동 개선 시스템 시작"""
        self.enabled = True
        logger.info("🤖 Auto-Improvement System started")
        
        while self.enabled:
            # 매일 자정까지 대기
            await self._wait_until_midnight()
            
            if self.enabled:
                await self._daily_improvement()
    
    def stop(self):
        """자동 개선 시스템 중지"""
        self.enabled = False
        logger.info("🛑 Auto-Improvement System stopped")
    
    async def _wait_until_midnight(self):
        """자정까지 대기"""
        now = datetime.now()
        tomorrow = datetime.combine(now.date(), time(0, 0)) + timedelta(days=1)
        seconds_until_midnight = (tomorrow - now).total_seconds()
        
        logger.info(f"⏰ Next auto-training in {seconds_until_midnight/3600:.1f} hours")
        await asyncio.sleep(seconds_until_midnight)
    
    async def _daily_improvement(self):
        """일일 자동 개선"""
        logger.info("🔄 Starting daily auto-improvement...")
        
        try:
            # 1. 어제 거래 성과 분석
            performance = await self._analyze_yesterday_performance()
            self.performance_history.append(performance)
            
            # 2. 재학습 결정
            should_retrain = self._should_retrain(performance)
            
            if should_retrain:
                logger.info("📚 Performance below threshold, retraining...")
                
                # 3. 최근 30일 데이터로 재학습
                model_path = await self._retrain_model(days=30)
                
                # 4. 백테스트로 검증
                backtest_result = await self._validate_model(model_path)
                
                # 5. 성과 비교 후 적용
                if backtest_result['total_return'] > performance.get('return', 0):
                    logger.info(f"✅ New model is better! Applying...")
                    self.last_training = datetime.now()
                else:
                    logger.info(f"⚠️ New model not better, keeping old one")
            else:
                logger.info("✅ Performance good, skipping retraining")
                
        except Exception as e:
            logger.error(f"❌ Daily improvement failed: {e}")
    
    async def _analyze_yesterday_performance(self):
        """어제 거래 성과 분석"""
        # 거래 히스토리에서 어제 데이터 가져오기
        # 실제 구현 시 데이터베이스에서 조회
        return {
            'date': datetime.now().date(),
            'trades': 10,
            'wins': 6,
            'losses': 4,
            'return': 2.5,  # %
            'sharpe': 1.2
        }
    
    def _should_retrain(self, performance):
        """재학습 필요 여부 판단"""
        # 승률이 50% 미만이면 재학습
        if len(self.performance_history) >= 3:
            recent_wins = [p.get('wins', 0) for p in self.performance_history[-3:]]
            recent_total = [p.get('trades', 1) for p in self.performance_history[-3:]]
            win_rate = sum(recent_wins) / max(sum(recent_total), 1)
            
            if win_rate < 0.5:
                return True
        
        # 수익률이 마이너스면 재학습
        if performance.get('return', 0) < 0:
            return True
            
        return False
    
    async def _retrain_model(self, days=30):
        """모델 재학습"""
        from datetime import timedelta
        
        # 최근 데이터로 학습
        model_path = await train_agent(
            symbol='BTCUSDT',
            interval='1m',
            days=days,
            episodes=1000,
            save_freq=100
        )
        
        logger.info(f"✅ Model retrained: {model_path}")
        return model_path
    
    async def _validate_model(self, model_path):
        """새 모델 검증 (백테스트)"""
        from ai.trainer import backtest_agent
        
        result = await backtest_agent(
            model_path=model_path,
            symbol='BTCUSDT',
            days=7  # 최근 7일로 검증
        )
        
        return result


# Global instance
auto_improver = None


async def start_auto_improvement(binance_client: BinanceClient):
    """자동 개선 시스템 시작"""
    global auto_improver
    
    if auto_improver is None:
        auto_improver = AutoImprover(binance_client)
        asyncio.create_task(auto_improver.start())
        logger.info("🚀 Auto-improvement task created")


def stop_auto_improvement():
    """자동 개선 시스템 중지"""
    global auto_improver
    
    if auto_improver:
        auto_improver.stop()
        auto_improver = None
