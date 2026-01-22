"""
Settings API Router
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from loguru import logger

router = APIRouter()


class RiskSettings(BaseModel):
    daily_loss_limit: Optional[float] = None
    daily_trade_limit: Optional[int] = None
    max_position_size: Optional[float] = None
    stop_loss_percent: Optional[float] = None
    take_profit_percent: Optional[float] = None
    trailing_stop: Optional[bool] = None


class NotificationSettings(BaseModel):
    desktop: bool = True
    email: bool = False
    telegram: bool = False


@router.get("/")
async def get_settings():
    """Get current settings"""
    try:
        from app.services.risk_manager import risk_manager
        from app.services.notifications import notification_manager
        
        return {
            "risk": {
                "daily_loss_limit": risk_manager.daily_loss_limit,
                "daily_trade_limit": risk_manager.daily_trade_limit,
                "max_position_size": risk_manager.max_position_size * 100,
                "stop_loss_percent": risk_manager.default_stop_loss_percent,
                "take_profit_percent": risk_manager.default_take_profit_percent,
                "trailing_stop": risk_manager.trailing_stop_enabled
            },
            "notifications": notification_manager.enabled_channels
        }
    except Exception as e:
        logger.error(f"Failed to get settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def update_settings(
    risk: Optional[RiskSettings] = None,
    notifications: Optional[NotificationSettings] = None,
    email: Optional[dict] = None,
    telegram: Optional[dict] = None
):
    """Update settings"""
    try:
        from app.services.risk_manager import risk_manager
        from app.services.notifications import notification_manager
        
        # Update risk settings
        if risk:
            risk_manager.update_settings(
                daily_loss_limit=risk.daily_loss_limit,
                daily_trade_limit=risk.daily_trade_limit,
                max_position_size=risk.max_position_size / 100 if risk.max_position_size else None,
                stop_loss_percent=risk.stop_loss_percent,
                take_profit_percent=risk.take_profit_percent,
                trailing_stop=risk.trailing_stop
            )
        
        # Update notification settings
        if notifications:
            notification_manager.enabled_channels = notifications.dict()
        
        if email:
            notification_manager.configure('email', email)
        
        if telegram:
            notification_manager.configure('telegram', telegram)
        
        return {"status": "updated"}
        
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk/status")
async def get_risk_status():
    """Get risk management status"""
    try:
        from app.services.risk_manager import risk_manager
        return risk_manager.get_status()
    except Exception as e:
        logger.error(f"Failed to get risk status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
