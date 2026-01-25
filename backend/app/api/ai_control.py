"""
AI Control API Router - FIXED VERSION
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from loguru import logger
import os
import pandas as pd
import json
from datetime import datetime, timedelta

from ai.agent import TradingAgent
from ai.trainer import train_agent, backtest_agent
from app.core.config import settings
from app.services.scheduler import SchedulerService

router = APIRouter()

# Global agent instance and scheduler
trading_agent: Optional[TradingAgent] = None
scheduler: Optional[SchedulerService] = None

training_status = {
    "is_training": False,
    "progress": 0,
    "current_episode": 0,
    "total_episodes": 0,
    "status": "idle"
}


class TrainingRequest(BaseModel):
    symbol: str = "BTCUSDT"
    interval: str = "1m"
    days: int = 30
    episodes: int = 1000
    leverage: int = 5
    stop_loss: float = 2.0
    take_profit: float = 5.0
    reward_strategy: str = "simple"


class BacktestRequest(BaseModel):
    model_path: str
    interval: str = "1h"  # Added interval support
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_balance: float = 10000.0
    days: int = 30


class OptimizationRequest(BaseModel):
    symbol: str = "BTCUSDT"
    interval: str = "1m"
    days: int = 30
    n_trials: int = 10


@router.get("/status")
async def get_status():
    """Get current AI status"""
    global trading_agent
    
    # Check if auto trading is running
    is_running = False
    active_agent = None
    
    try:
        from app.main import auto_trading_service
        if auto_trading_service:
            is_running = auto_trading_service.running
            active_agent = auto_trading_service.agent
    except Exception as e:
        logger.warning(f"Failed to access auto_trading_service: {e}")
        is_running = False
    
    # Use the active agent from the service if available, otherwise fall back to local global
    target_agent = active_agent if active_agent else trading_agent
    
    if target_agent is None:
        target_agent = TradingAgent()
        # Update local global if it was None
        if trading_agent is None:
            trading_agent = target_agent
    
    model_info = target_agent.get_model_info()
    
    return {
        "model_loaded": target_agent.model is not None,
        "model_info": model_info,
        "training_status": training_status,
        "running": is_running
    }


@router.post("/start")
async def start_ai():
    """Start AI auto trading"""
    try:
        from app.main import auto_trading_service
        
        if auto_trading_service is None:
            raise HTTPException(status_code=500, detail="Auto trading service not initialized")
        
        if auto_trading_service.running:
            return {
                "status": "already_running",
                "message": "AI auto trading is already running"
            }
        
        await auto_trading_service.start()
        
        return {
            "status": "success",
            "message": "AI auto trading started",
            "running": True
        }
    except Exception as e:
        logger.error(f"Failed to start AI: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_ai():
    """Stop AI auto trading"""
    try:
        from app.main import auto_trading_service
        
        if auto_trading_service is None:
            raise HTTPException(status_code=500, detail="Auto trading service not initialized")
        
        if not auto_trading_service.running:
            return {
                "status": "already_stopped",
                "message": "AI auto trading is not running"
            }
        
        await auto_trading_service.stop()
        
        return {
            "status": "success",
            "message": "AI auto trading stopped",
            "running": False
        }
    except Exception as e:
        logger.error(f"Failed to stop AI: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train")
async def train_model(request: TrainingRequest, background_tasks: BackgroundTasks):
    """Start training the AI model"""
    global trading_agent, training_status
    
    if training_status["is_training"]:
        raise HTTPException(status_code=400, detail="Training already in progress")
    
    try:
        # Initialize agent if needed
        if trading_agent is None:
            trading_agent = TradingAgent()
        
        # Run training in background
        background_tasks.add_task(
            run_training_task,
            symbol=request.symbol,
            interval=request.interval,
            days=request.days,
            episodes=request.episodes,
            leverage=request.leverage,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
            reward_strategy=request.reward_strategy
        )
        
        return {
            "status": "success",
            "message": "Training started in background"
        }
        
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_training_task(
    symbol: str,
    interval: str,
    days: int,
    episodes: int,
    leverage: int,
    stop_loss: float,
    take_profit: float,
    reward_strategy: str
):
    """Background task for training"""
    global trading_agent, training_status
    
    training_status["is_training"] = True
    training_status["progress"] = 0
    training_status["status"] = "Training..."
    
    try:
        model_path = await train_agent(
            symbol=symbol,
            interval=interval,
            days=days,
            episodes=episodes,
            leverage=leverage,
            reward_strategy=reward_strategy
        )
        
        # Load the trained model
        if model_path and os.path.exists(model_path):
            trading_agent.load_model(model_path)
            training_status["status"] = f"Training completed! Model: {os.path.basename(model_path)}"
        else:
            training_status["status"] = "Training completed but model not found"
            
    except Exception as e:
        logger.error(f"Training task failed: {e}")
        training_status["status"] = f"Training failed: {str(e)}"
    finally:
        training_status["is_training"] = False


@router.post("/optimize")
async def optimize_hyperparameters(request: OptimizationRequest, background_tasks: BackgroundTasks):
    """
    Run hyperparameter optimization
    FIXED: Changed training_agent to trading_agent
    """
    global trading_agent, training_status
    
    if training_status["is_training"]:
        raise HTTPException(status_code=400, detail="Training/Optimization already in progress")
    
    try:
        # Initialize agent if needed
        if trading_agent is None:
            trading_agent = TradingAgent()
        
        # Fetch data for optimization
        from trading.exchange_factory import ExchangeFactory
        exchange_client = await ExchangeFactory.get_client()
        
        # Validate days
        days = request.days if request.days and request.days > 0 else 7
        
        # Calculate limit based on interval
        candles_per_day = {
            "1m": 1440,
            "5m": 288,
            "15m": 96,
            "1h": 24,
            "4h": 6,
            "1d": 1
        }
        limit = int(days * candles_per_day.get(request.interval, 24))
        
        # Binance API single request limit is usually 1000. 
        # For optimization we need more data. 
        # If we use fetch_training_data logic it handles it (but trainer.py has a bug capping it at 1000).
        # We should use fetch_training_data from trainer.py to be consistent and robust.
        from ai.trainer import fetch_training_data
        
        df = await fetch_training_data(
            symbol=request.symbol,
            interval=request.interval,
            days=days
        )
        
        # from ai.features import add_technical_indicators # Already done in fetch_training_data
        # df = add_technical_indicators(df) 
        
        # await client.close() # No longer needed as fetch_training_data handles it
        
        # Run optimization in background
        background_tasks.add_task(
            run_optimization_task,
            df=df,
            n_trials=request.n_trials
        )
        
        return {
            "status": "success",
            "message": f"Optimization started with {request.n_trials} trials"
        }
        
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_optimization_task(df, n_trials=10):
    """
    Background task for optimization
    FIXED: Proper error handling and result checking
    """
    global trading_agent, training_status
    
    training_status["is_training"] = True
    training_status["progress"] = 0
    training_status["status"] = "Optimizing hyperparameters..."
    
    try:
        # Save dataframe for optimizer
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_path = f.name
            df.to_csv(temp_path, index=False)
        
        # Run optimization using HyperOptimizer directly
        from ai.optimization import HyperOptimizer
        
        optimizer = HyperOptimizer(
            data_path=temp_path,
            n_trials=n_trials,
            study_name=f"ppo_opt_{int(pd.Timestamp.now().timestamp())}"
        )
        
        best_params, best_value = optimizer.run_optimization()
        
        # Check if optimization was successful
        if not best_params:
            training_status["status"] = "Optimization failed: No successful trials"
            logger.warning("Optimization completed but no successful trials")
            return
        
        # Update agent with best parameters
        if trading_agent:
            trading_agent.learning_rate = best_params.get('learning_rate', 0.0003)
            trading_agent.gamma = best_params.get('gamma', 0.99)
            trading_agent.batch_size = best_params.get('batch_size', 64)
            trading_agent.n_epochs = best_params.get('n_epochs', 10)
        
        training_status["status"] = (
            f"✅ Optimization complete! "
            f"LR={best_params.get('learning_rate', 0):.5f}, "
            f"Gamma={best_params.get('gamma', 0):.4f}, "
            f"Score={best_value:.2f}"
        )
        
        logger.success(f"Optimization results: {best_params}")
        
        # Cleanup temp file
        try:
            os.remove(temp_path)
        except:
            pass
        
    except Exception as e:
        logger.error(f"Optimization task failed: {e}", exc_info=True)
        training_status["status"] = f"❌ Optimization failed: {str(e)[:100]}"
    finally:
        training_status["is_training"] = False


@router.post("/backtest")
async def run_backtest(request: BacktestRequest):
    """Run backtest on historical data"""
    try:
        # Resolve model path
        model_path = request.model_path
        if not os.path.exists(model_path):
             path_in_model_dir = os.path.join(settings.AI_MODEL_PATH, model_path)
             if os.path.exists(path_in_model_dir):
                 model_path = path_in_model_dir
             elif model_path.startswith("data/models/"):
                 basename = os.path.basename(model_path)
                 path_in_model_dir = os.path.join(settings.AI_MODEL_PATH, basename)
                 if os.path.exists(path_in_model_dir):
                     model_path = path_in_model_dir
                     
        if not os.path.exists(model_path):
            raise HTTPException(status_code=404, detail=f"Model file not found: {request.model_path}")

        results = await backtest_agent(
            model_path=model_path,
            interval=request.interval,  # Pass interval to agent
            start_date=request.start_date,
            end_date=request.end_date,
            initial_balance=request.initial_balance,
            days=request.days
        )
        
        return {
            "status": "success",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/models/{model_name}")
async def delete_model(model_name: str):
    """Delete a trained model"""
    try:
        model_dir = settings.AI_MODEL_PATH
        model_path = os.path.join(model_dir, model_name)
        
        if not os.path.exists(model_path):
            raise HTTPException(status_code=404, detail="Model not found")
        
        # Check if model is currently loaded
        # Note: Skip this check as TradingAgent may not have current_model_path attribute
        # Users should manually ensure they're not deleting the active model
        
        # Delete the model file
        os.remove(model_path)
        logger.info(f"Model deleted: {model_name}")
        
        return {
            "status": "success",
            "message": f"Model {model_name} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_models():
    """List available trained models"""
    try:
        model_dir = settings.AI_MODEL_PATH
        
        if not os.path.exists(model_dir):
            return {"models": []}
        
        models = []
        for filename in os.listdir(model_dir):
            if filename.endswith('.zip'):
                filepath = os.path.join(model_dir, filename)
                stat = os.stat(filepath)
                
                models.append({
                    "filename": filename,
                    "path": filepath,
                    "size": stat.st_size,
                    "modified": stat.st_mtime
                })
        
        # Sort by modified time (newest first)
        models.sort(key=lambda x: x['modified'], reverse=True)
        
        return {"models": models}
        
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class LoadModelRequest(BaseModel):
    model_path: str


@router.post("/models/load")
async def load_model(request: LoadModelRequest):
    """Load a specific model"""
    global trading_agent
    
    try:
        model_path = request.model_path
        
        # Check if just filename was passed
        if not os.path.exists(model_path):
             path_in_model_dir = os.path.join(settings.AI_MODEL_PATH, model_path)
             if os.path.exists(path_in_model_dir):
                 model_path = path_in_model_dir
             # Also handle "data/models/..." prefix passed from frontend
             elif model_path.startswith("data/models/"):
                 basename = os.path.basename(model_path)
                 path_in_model_dir = os.path.join(settings.AI_MODEL_PATH, basename)
                 if os.path.exists(path_in_model_dir):
                     model_path = path_in_model_dir
        
        if not os.path.exists(model_path):
            raise HTTPException(status_code=404, detail=f"Model file not found: {request.model_path}")
        
        if trading_agent is None:
            trading_agent = TradingAgent()
        
        trading_agent.load_model(model_path)
        
        # SYNC with AutoTradingService
        # Critical Fix: Ensure the running auto-trader uses this new model
        import app.main as main
        if main.auto_trading_service:
            # Inject the loaded agent into the service
            main.auto_trading_service.agent = trading_agent
            logger.info("Synced loaded model with AutoTradingService")
        
        return {
            "status": "success",
            "message": f"Model loaded: {os.path.basename(model_path)}"
        }
        
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/models/{filename}")
async def delete_model(filename: str):
    """Delete a model file"""
    try:
        model_path = os.path.join(settings.AI_MODEL_PATH, filename)
        
        if not os.path.exists(model_path):
            raise HTTPException(status_code=404, detail="Model file not found")
        
        os.remove(model_path)
        
        # Also remove history file if exists
        history_path = model_path.replace('.zip', '_history.json')
        if os.path.exists(history_path):
            os.remove(history_path)
        
        return {
            "status": "success",
            "message": f"Model deleted: {filename}"
        }
        
    except Exception as e:
        logger.error(f"Failed to delete model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class BatchDeleteRequest(BaseModel):
    model_names: list[str]


@router.post("/models/batch-delete")
async def batch_delete_models(request: BatchDeleteRequest):
    """Delete multiple models at once"""
    try:
        model_dir = settings.AI_MODEL_PATH
        deleted_count = 0
        errors = []
        
        for name in request.model_names:
            try:
                model_path = os.path.join(model_dir, name)
                if os.path.exists(model_path):
                    os.remove(model_path)
                    
                    # Remove history
                    history_path = model_path.replace('.zip', '_history.json')
                    if os.path.exists(history_path):
                        os.remove(history_path)
                    
                    deleted_count += 1
            except Exception as e:
                errors.append(f"{name}: {str(e)}")
        
        return {
            "status": "success", 
            "deleted": deleted_count, 
            "errors": errors if errors else None
        }
        
    except Exception as e:
        logger.error(f"Batch delete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class AgentManager:
    """Wrapper to allow scheduler to trigger training"""
    async def train_model_auto(self):
        """Trigger automated retraining with default parameters"""
        logger.info("Scheduler triggered auto-retraining")
        if training_status["is_training"]:
            logger.warning("Training already in progress, skipping auto-retrain")
            return

        # Use default parameters for auto-retraining
        # These could be moved to settings or scheduler config
        await run_training_task(
            symbol="BTCUSDT",
            interval="1h",
            days=90,
            episodes=1000,
            leverage=5,
            stop_loss=2.0,
            take_profit=4.0,
            reward_strategy="simple"
        )


# Scheduler endpoints
@router.get("/scheduler/config")
async def get_scheduler_config():
    """Get scheduler configuration"""
    global scheduler
    
    if scheduler is None:
        from app.services.scheduler import SchedulerService
        scheduler = SchedulerService(agent_manager=AgentManager())
    
    return scheduler.get_config()


@router.post("/scheduler/config")
async def update_scheduler_config(config: dict):
    """Update scheduler configuration"""
    global scheduler
    
    if scheduler is None:
        from app.services.scheduler import SchedulerService
        scheduler = SchedulerService(agent_manager=AgentManager())
    
    scheduler.update_config(config)
    
    return {
        "status": "success",
        "config": scheduler.get_config()
    }

def get_scheduler():
    """Get global scheduler instance"""
    global scheduler
    if scheduler is None:
        from app.services.scheduler import SchedulerService
        scheduler = SchedulerService(agent_manager=AgentManager())
    return scheduler


# Daily Review & Learning endpoints
@router.get("/daily-review")
async def get_daily_review():
    """Get latest daily review report"""
    try:
        review_path = "data/logs/daily_review_latest.json"
        if not os.path.exists(review_path):
            # Return empty structure instead of status object
            return {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "total_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "patterns": ["No data available yet - trade to generate insights"],
                "mistakes": [],
                "recommendations": ["Start trading to collect data for AI analysis"]
            }
        
        with open(review_path, 'r') as f:
            review_data = json.load(f)
        
        # Ensure all required fields exist
        review_data.setdefault('patterns', [])
        review_data.setdefault('mistakes', [])
        review_data.setdefault('recommendations', [])
        review_data.setdefault('total_trades', 0)
        review_data.setdefault('win_rate', 0)
        review_data.setdefault('total_pnl', 0)
        review_data.setdefault('avg_win', 0)
        review_data.setdefault('avg_loss', 0)
        
        return review_data
    except Exception as e:
        logger.error(f"Failed to get daily review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-daily-review")
async def trigger_daily_review():
    """Manually trigger daily review"""
    try:
        from ai.daily_review import DailyReviewAnalyzer as DailyReviewer
        from trading.exchange_factory import ExchangeFactory
        
        exchange_client = await ExchangeFactory.get_client()
        
        try:
            # Fetch raw trades from exchange
            raw_trades = await exchange_client.get_user_trades(limit=100)
            
            # Map Binance fields to Analyzer schema
            trades = []
            for t in raw_trades:
                trades.append({
                    "pnl": float(t.get('realizedPnl', 0)),
                    "timestamp": datetime.fromtimestamp(t['time'] / 1000.0).isoformat(),
                    "side": "LONG" if t['side'] == 'BUY' else "SHORT",
                    "quantity": float(t.get('qty', 0)),
                    "price": float(t.get('price', 0)),
                    "symbol": t['symbol']
                })
            
            reviewer = DailyReviewer(data_dir="data/reviews")
            report = reviewer.analyze_daily_performance(trades)
            
            # Additional: Generate improvement suggestions based on metrics
            suggestions = reviewer.suggest_ai_improvements()
            
            os.makedirs("data/logs", exist_ok=True)
            with open("data/logs/improvement_suggestions.json", 'w') as f:
                json.dump(suggestions, f, indent=2)
        finally:
            pass # Managed by factory
        
        # Save report
        os.makedirs("data/logs", exist_ok=True)
        with open("data/logs/daily_review_latest.json", 'w') as f:
            json.dump(report, f, indent=2)
        
        return {
            "status": "success",
            "report": report
        }
    except Exception as e:
        logger.error(f"Daily review failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/improvement-suggestions")
async def get_improvement_suggestions():
    """Get AI improvement suggestions"""
    try:
        suggestions_path = "data/logs/improvement_suggestions.json"
        if not os.path.exists(suggestions_path):
            return {
                "status": "no_data",
                "suggestions": []
            }
        
        with open(suggestions_path, 'r') as f:
            suggestions = json.load(f)
        
        return {
            "status": "success",
            "suggestions": suggestions
        }
    except Exception as e:
        logger.error(f"Failed to get suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weekly-summary")
async def get_weekly_summary():
    """Get weekly performance summary"""
        # Calculate weekly stats from trade history
        from trading.exchange_factory import ExchangeFactory
        
        exchange_client = await ExchangeFactory.get_client()
        
        try:
            # Get trades from last 7 days
            end_time = datetime.now()
            start_time = end_time - timedelta(days=7)
            
            # Correctly call the underlying client for time-limited trades
            # Using binance-specific attributes if available, otherwise generic
            if hasattr(exchange_client, 'client') and hasattr(exchange_client.client, 'futures_account_trades'):
                trades = await exchange_client.client.futures_account_trades(
                    symbol="BTCUSDT",
                    startTime=int(start_time.timestamp() * 1000),
                    endTime=int(end_time.timestamp() * 1000)
                )
            else:
                trades = await exchange_client.get_user_trades(limit=100) # Fallback
        finally:
            pass # Managed by factory
        
        if not trades:
            return {
                "status": "no_data",
                "message": "No trades in the last 7 days"
            }
        
        # Calculate stats
        total_trades = len(trades)
        total_pnl = sum(float(t.get('realizedPnl', 0)) for t in trades)
        winning_trades = sum(1 for t in trades if float(t.get('realizedPnl', 0)) > 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        return {
            "status": "success",
            "period": "Last 7 days",
            "total_trades": total_trades,
            "win_rate": round(win_rate, 2),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl_per_trade": round(total_pnl / total_trades, 2) if total_trades > 0 else 0
        }
    except Exception as e:
        logger.error(f"Weekly summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class LoadModelSimpleRequest(BaseModel):
    model_name: str


@router.post("/load-model")
async def load_model_endpoint(request: LoadModelSimpleRequest):
    """Load a specific model"""
    global trading_agent
    
    try:
        if trading_agent is None:
            trading_agent = TradingAgent()
        
        model_path = request.model_name
        
        # Check if just filename was passed
        if not os.path.exists(model_path):
            path_in_model_dir = os.path.join(settings.AI_MODEL_PATH, model_path)
            if os.path.exists(path_in_model_dir):
                model_path = path_in_model_dir
            # Also handle "data/models/..." prefix passed from frontend
            elif model_path.startswith("data/models/"):
                basename = os.path.basename(model_path)
                path_in_model_dir = os.path.join(settings.AI_MODEL_PATH, basename)
                if os.path.exists(path_in_model_dir):
                    model_path = path_in_model_dir
        
        if not os.path.exists(model_path):
            raise HTTPException(status_code=404, detail=f"Model file not found: {request.model_name}")
        
        trading_agent.load_model(model_path)
        
        # SYNC with AutoTradingService
        import app.main as main
        if main.auto_trading_service:
            main.auto_trading_service.agent = trading_agent
            logger.info("Synced loaded model with AutoTradingService")
        
        return {
            "status": "success",
            "message": f"Model {os.path.basename(model_path)} loaded successfully"
        }
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise HTTPException(status_code=500, detail=str(e))
