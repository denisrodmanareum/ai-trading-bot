"""
API endpoints for Balance-Based Strategy Manager
"""
from fastapi import APIRouter, HTTPException
from typing import Dict
from loguru import logger

router = APIRouter(prefix="/api/balance-strategy", tags=["balance-strategy"])


@router.get("/tier-info")
async def get_tier_info() -> Dict:
    """
    Get current balance tier information
    
    Returns:
        tier_name: Current tier (MICRO/SMALL/MEDIUM/LARGE)
        balance_range: Balance range for the tier
        core_ratio: Core coin position ratio
        alt_ratio: Alt coin position ratio
        recent_winrate: Recent win rate
        recovery_mode: Whether recovery mode is active
    """
    try:
        from app.main import auto_trading_service
        
        if not auto_trading_service:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        # Get current balance
        try:
            account = await auto_trading_service.exchange_client.get_account_info()
            current_balance = account.get('balance', 5000.0)
        except Exception:
            current_balance = 5000.0
        
        # Get tier info
        tier_info = auto_trading_service.balance_strategy.get_tier_info(current_balance)
        
        return {
            "status": "success",
            "balance": current_balance,
            **tier_info
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tier info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent-trades")
async def get_recent_trades() -> Dict:
    """
    Get recent trade history from strategy manager
    
    Returns:
        trades: List of recent trades with PnL and win/loss status
    """
    try:
        from app.main import auto_trading_service
        
        if not auto_trading_service:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        recent_trades = auto_trading_service.balance_strategy.recent_trades
        
        return {
            "status": "success",
            "count": len(recent_trades),
            "trades": recent_trades[-10:]  # Last 10 trades
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recent trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-stats")
async def reset_stats() -> Dict:
    """
    Reset balance strategy statistics
    
    This will clear recent trade history and reset recovery mode
    """
    try:
        from app.main import auto_trading_service
        
        if not auto_trading_service:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        auto_trading_service.balance_strategy.reset_stats()
        
        logger.info("Balance strategy stats reset by user")
        
        return {
            "status": "success",
            "message": "Statistics reset successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily-limit-status")
async def get_daily_limit_status() -> Dict:
    """
    Get daily trade limit status
    
    Returns:
        current_count: Number of trades today
        max_trades: Maximum trades allowed
        can_trade: Whether more trades are allowed today
    """
    try:
        from app.main import auto_trading_service
        
        if not auto_trading_service:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        # Get current balance
        try:
            account = await auto_trading_service.exchange_client.get_account_info()
            current_balance = account.get('balance', 5000.0)
        except Exception:
            current_balance = 5000.0
        
        can_trade, msg = auto_trading_service.balance_strategy.check_daily_trade_limit(current_balance)
        tier = auto_trading_service.balance_strategy.get_current_tier(current_balance)
        
        return {
            "status": "success",
            "current_count": auto_trading_service.balance_strategy.daily_trade_count,
            "max_trades": tier["max_daily_trades"],
            "can_trade": can_trade,
            "message": msg
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get daily limit status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
