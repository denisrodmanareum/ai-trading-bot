"""
Settings API Router
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from loguru import logger
import os
import asyncio
from app.core.config import settings

router = APIRouter()


class RiskSettings(BaseModel):
    daily_loss_limit: Optional[float] = None
    max_margin_level: Optional[float] = None
    position_mode: Optional[str] = None # FIXED, RATIO, ADAPTIVE
    position_ratio: Optional[float] = None
    max_total_exposure: Optional[float] = None
    kill_switch: Optional[bool] = None
    core_coin_ratio: Optional[float] = None
    alt_coin_ratio: Optional[float] = None


class NotificationSettings(BaseModel):
    desktop: bool = True
    email: bool = False
    telegram: bool = False


class TelegramNotificationSettings(BaseModel):
    enabled: bool = False
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None


class TelegramTestRequest(BaseModel):
    message: Optional[str] = None
    # Allow testing with unsaved inputs
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None


@router.get("/")
async def get_settings():
    """Get current settings"""
    try:
        import app.main as main
        from app.services.notifications import notification_manager
        
        # Guard if service not ready
        if not main.auto_trading_service:
            # Return defaults if service not started yet
            return {
                "risk": {},
                "notifications": notification_manager.enabled_channels
            }

        rc = main.auto_trading_service.risk_config
        return {
            "risk": {
                "daily_loss_limit": rc.daily_loss_limit,
                "max_margin_level": rc.max_margin_level,
                "position_mode": rc.position_mode,
                "position_ratio": rc.position_ratio,
                "max_total_exposure": rc.max_total_exposure,
                "kill_switch": rc.kill_switch,
                "core_coin_ratio": rc.core_coin_ratio,
                "alt_coin_ratio": rc.alt_coin_ratio,
            },
            "notifications": notification_manager.enabled_channels
        }
    except HTTPException:
        raise
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
        import app.main as main
        from app.services.notifications import notification_manager
        
        if main.auto_trading_service and risk:
            main.auto_trading_service.update_risk_config(
                daily_loss_limit=risk.daily_loss_limit,
                max_margin_level=risk.max_margin_level,
                kill_switch=risk.kill_switch,
                position_mode=risk.position_mode,
                position_ratio=risk.position_ratio,
                max_total_exposure=risk.max_total_exposure,
                core_coin_ratio=risk.core_coin_ratio,
                alt_coin_ratio=risk.alt_coin_ratio
            )
        
        # Update notification settings
        if notifications:
            notification_manager.enabled_channels = notifications.dict()
        
        if email:
            notification_manager.configure('email', email)
        
        if telegram:
            notification_manager.configure('telegram', telegram)
        
        return {"status": "updated"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk/status")
async def get_risk_status():
    """Get risk management status"""
    try:
        import app.main as main
        if not main.auto_trading_service:
             return {"status": "starting", "risk_status": "NORMAL"}
             
        return {
            "risk_status": main.auto_trading_service.risk_status,
            "daily_loss": main.auto_trading_service.current_daily_loss,
            "margin_level": main.auto_trading_service.last_margin_level,
            "kill_switch": main.auto_trading_service.risk_config.kill_switch
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get risk status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications")
async def get_notification_settings():
    """Get enabled notification channels"""
    try:
        from app.services.notifications import notification_manager
        return notification_manager.enabled_channels
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get notification settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications")
async def update_notification_settings(settings: NotificationSettings):
    """Update enabled notification channels"""
    try:
        from app.services.notifications import notification_manager
        notification_manager.enabled_channels = settings.dict()
        # persist
        if hasattr(notification_manager, "_save_to_disk"):
            notification_manager._save_to_disk()
        return {"status": "updated", "notifications": notification_manager.enabled_channels}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update notification settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications/telegram")
async def get_telegram_settings():
    """Get telegram notification config (token is not returned for security)"""
    try:
        from app.services.notifications import notification_manager
        bot_token = (notification_manager.telegram_config.get("bot_token") or "").strip()
        chat_id = (notification_manager.telegram_config.get("chat_id") or "").strip()
        enabled = bool(notification_manager.enabled_channels.get("telegram", False))
        return {
            "enabled": enabled,
            "chat_id": chat_id,
            "bot_token_configured": bool(bot_token),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get telegram settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications/telegram")
async def save_telegram_settings(settings: TelegramNotificationSettings):
    """Save telegram config + enable/disable"""
    try:
        from app.services.notifications import notification_manager

        # Update stored config only when a non-empty value is provided
        updates: dict = {}
        if settings.bot_token is not None and settings.bot_token.strip():
            updates["bot_token"] = settings.bot_token.strip()
        if settings.chat_id is not None and str(settings.chat_id).strip():
            updates["chat_id"] = str(settings.chat_id).strip()

        if updates:
            notification_manager.configure("telegram", updates)

        notification_manager.enabled_channels["telegram"] = bool(settings.enabled)
        if hasattr(notification_manager, "_save_to_disk"):
            notification_manager._save_to_disk()

        return {
            "status": "updated",
            "enabled": notification_manager.enabled_channels.get("telegram", False),
            "chat_id": notification_manager.telegram_config.get("chat_id", ""),
            "bot_token_configured": bool((notification_manager.telegram_config.get("bot_token") or "").strip()),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save telegram settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications/telegram/test")
async def test_telegram_notification(req: TelegramTestRequest):
    """Send a test telegram message"""
    try:
        from app.services.notifications import notification_manager, NotificationType

        # Temporarily use provided settings (do not persist)
        bot_token = (req.bot_token or notification_manager.telegram_config.get("bot_token") or "").strip()
        chat_id = (req.chat_id or notification_manager.telegram_config.get("chat_id") or "").strip()
        if not bot_token or not chat_id:
            raise HTTPException(status_code=400, detail="Telegram bot_token/chat_id not configured")

        # Temporarily override for this call
        prev = dict(notification_manager.telegram_config)
        try:
            notification_manager.telegram_config["bot_token"] = bot_token
            notification_manager.telegram_config["chat_id"] = chat_id
            msg = req.message or "✅ 텔레그램 알림 테스트 메시지입니다. (AI Trading Bot)"
            await notification_manager.send(NotificationType.PRICE_ALERT, "Telegram Test", msg, channels=["telegram"])
        finally:
            notification_manager.telegram_config = prev

        return {"status": "sent"}
    except HTTPException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Telegram test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- API Configuration Models ---

class ApiConfig(BaseModel):
    active_exchange: str
    binance_key: str
    bybit_key: str
    testnet: bool

class ApiConfigUpdate(BaseModel):
    active_exchange: str  # "BINANCE" or "BYBIT"
    binance_key: Optional[str] = None
    binance_secret: Optional[str] = None
    bybit_key: Optional[str] = None
    bybit_secret: Optional[str] = None
    testnet: bool

# --- API Configuration Endpoints ---

@router.get("/api-config", response_model=ApiConfig)
async def get_api_config():
    """Get current exchange configuration (masked)"""
    return {
        "active_exchange": settings.ACTIVE_EXCHANGE,
        "binance_key": f"{settings.BINANCE_API_KEY[:4]}...{settings.BINANCE_API_KEY[-4:]}" if len(settings.BINANCE_API_KEY) > 8 else "****",
        "bybit_key": f"{settings.BYBIT_API_KEY[:4]}...{settings.BYBIT_API_KEY[-4:]}" if len(settings.BYBIT_API_KEY) > 8 else "****",
        "testnet": settings.BINANCE_TESTNET # Using Binance testnet flag as global for now
    }

@router.post("/api-config")
async def update_api_config(config: ApiConfigUpdate):
    """Update API configuration and exchange selection"""
    try:
        # 1. Update memory
        if config.active_exchange not in ["BINANCE", "BYBIT"]:
            raise HTTPException(status_code=400, detail="Invalid exchange")
            
        settings.ACTIVE_EXCHANGE = config.active_exchange
        if config.binance_key: settings.BINANCE_API_KEY = config.binance_key
        if config.binance_secret: settings.BINANCE_API_SECRET = config.binance_secret
        if config.bybit_key: settings.BYBIT_API_KEY = config.bybit_key
        if config.bybit_secret: settings.BYBIT_API_SECRET = config.bybit_secret
        settings.BINANCE_TESTNET = config.testnet
        settings.BYBIT_TESTNET = config.testnet
        
        # 2. Update .env file
        env_path = ".env"
        # Find path if running from backend
        if not os.path.exists(env_path):
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
            
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        
        keys = {
            "ACTIVE_EXCHANGE": settings.ACTIVE_EXCHANGE,
            "BINANCE_API_KEY": settings.BINANCE_API_KEY,
            "BINANCE_API_SECRET": settings.BINANCE_API_SECRET,
            "BYBIT_API_KEY": settings.BYBIT_API_KEY,
            "BYBIT_API_SECRET": settings.BYBIT_API_SECRET,
            "BINANCE_TESTNET": str(settings.BINANCE_TESTNET).lower(),
            "BYBIT_TESTNET": str(settings.BYBIT_TESTNET).lower()
        }
        
        new_lines = []
        handled = set()
        for line in lines:
            found = False
            for k in keys:
                if line.startswith(f"{k}="):
                    new_lines.append(f"{k}={keys[k]}\n")
                    handled.add(k)
                    found = True
                    break
            if not found:
                new_lines.append(line)
                
        for k in keys:
            if k not in handled:
                new_lines.append(f"{k}={keys[k]}\n")
                
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
            
        # 3. Reload Exchange Client
        from trading.exchange_factory import ExchangeFactory
        await ExchangeFactory.reload()
        
        return {"status": "success", "message": f"Updated to {config.active_exchange}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update API config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
