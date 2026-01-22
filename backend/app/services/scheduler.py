from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from datetime import datetime
import asyncio

from app.core.config import settings
# We need to access the global trading agent and status
# Ideally these should be singletons or passed in. 
# For now, we will import them from ai_control (circular import risk? ai_control imports agent)
# Better: Import agent from where it is instantiated or passed to init.
# But agent is global in ai_control. 
# Let's create a service that takes the agent as dependency.

class SchedulerService:
    def __init__(self, agent_manager):
        """
        Args:
            agent_manager: Reference to the component managing the AI agent (e.g. wrapper around agent)
        """
        self.scheduler = AsyncIOScheduler()
        self.agent_manager = agent_manager
        self.is_running = False
        self.config = {
            "enabled": False,
            "min_win_rate": 50.0,
            "check_interval_hours": 24,
            "retrain_on_loss": True
        }
        
    def get_config(self):
        """Get current configuration"""
        return self.config
        
    def start(self):
        if self.is_running:
            return
            
        self.scheduler.start()
        self.is_running = True
        
        # Add default jobs
        # 1. Daily Health Check & potentially Retrain
        self.scheduler.add_job(
            self.check_and_retrain,
            IntervalTrigger(hours=self.config["check_interval_hours"]),
            id="auto_retrain_job",
            replace_existing=True
        )
        
        logger.info("✅ Scheduler Service started")
        
    def stop(self):
        if not self.is_running:
            return
        self.scheduler.shutdown()
        self.is_running = False
        logger.info("🛑 Scheduler Service stopped")
        
    def update_config(self, new_config: dict):
        self.config.update(new_config)
        # Reschedule if needed
        if "check_interval_hours" in new_config:
            self.scheduler.reschedule_job(
                "auto_retrain_job",
                trigger=IntervalTrigger(hours=self.config["check_interval_hours"])
            )
        logger.info(f"Scheduler config updated: {self.config}")

    async def check_and_retrain(self):
        if not self.config["enabled"]:
            logger.info("Skipping auto-retrain (disabled)")
            return
            
        logger.info("Running Auto-Retrain Check...")
        
        # 1. Check Win Rate from DB (Phase 2 feature)
        # We need to query DB. 
        try:
            from app.database import SessionLocal
            from app.models import Trade
            from sqlalchemy import select, func, desc
            
            async with SessionLocal() as session:
                # Get last 50 trades
                query = select(Trade).order_by(desc(Trade.timestamp)).limit(50)
                result = await session.execute(query)
                trades = result.scalars().all()
                
                if not trades:
                    logger.info("Not enough trades to evaluate.")
                    return
                    
                wins = sum(1 for t in trades if t.pnl > 0)
                win_rate = (wins / len(trades)) * 100
                
                logger.info(f"Recent Win Rate (last {len(trades)}): {win_rate:.2f}%")
                
                if win_rate < self.config["min_win_rate"]:
                    logger.warning(f"Win Rate {win_rate:.2f}% < Threshold {self.config['min_win_rate']}%. Triggering Retraining!")
                    await self.trigger_retraining()
                else:
                    logger.info("Performance is acceptable.")
                    
        except Exception as e:
            logger.error(f"Auto-retrain check failed: {e}")

    async def trigger_retraining(self):
        # Trigger training via agent manager
        # This assumes agent_manager has a method to start training
        logger.info("🚀 Starting Automated Retraining...")
        
        # Run in background to not block scheduler
        # agent.train takes time. 
        # We should use the existing training logic if possible.
        
        # For simplicity, we assume we can call the same logic as the API.
        # But we don't have access to the API function directly easily.
        # We will assume agent_manager is the "trainer" module or similar.
        
        # Actually, let's just use the global agent reference if passed.
        if hasattr(self.agent_manager, 'train_model_auto'):
             await self.agent_manager.train_model_auto()
        else:
            logger.error("Agent manager does not support auto training")

