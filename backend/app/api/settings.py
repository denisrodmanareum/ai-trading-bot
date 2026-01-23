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
    daily_trade_limit: Optional[int] = None
    max_position_size: Optional[float] = None
    stop_loss_percent: Optional[float] = None
    take_profit_percent: Optional[float] = None
    trailing_stop: Optional[bool] = None


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


@router.get("/notifications")
async def get_notification_settings():
    """Get enabled notification channels"""
    try:
        from app.services.notifications import notification_manager
        return notification_manager.enabled_channels
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
    except Exception as e:
        logger.error(f"Telegram test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- API Configuration Models ---

class ApiConfig(BaseModel):
    api_key: str
    api_secret: str
    testnet: bool

class ApiConfigUpdate(BaseModel):
    api_key: str
    api_secret: str
    testnet: bool

# --- API Configuration Endpoints ---

@router.get("/api-config", response_model=ApiConfig)
async def get_api_config():
    """Run-time API configuration (masked)"""
    return {
        "api_key": f"{settings.BINANCE_API_KEY[:4]}...{settings.BINANCE_API_KEY[-4:]}" if settings.BINANCE_API_KEY and len(settings.BINANCE_API_KEY) > 8 else "****",
        "api_secret": "****", # Always mask secret
        "testnet": settings.BINANCE_TESTNET
    }

@router.post("/api-config")
async def update_api_config(config: ApiConfigUpdate):
    """
    Update API keys and Testnet setting.
    1. Updates memory settings.
    2. Updates .env file.
    3. Re-initializes Binance Client.
    """
    try:
        # 1. Update memory
        settings.BINANCE_API_KEY = config.api_key
        settings.BINANCE_API_SECRET = config.api_secret
        settings.BINANCE_TESTNET = config.testnet
        
        # 2. Update .env file
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
        
        # Read existing lines
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        
        new_lines = []
        keys_updated = {"BINANCE_API_KEY": False, "BINANCE_API_SECRET": False, "BINANCE_TESTNET": False}
        
        for line in lines:
            if line.startswith("BINANCE_API_KEY="):
                new_lines.append(f"BINANCE_API_KEY={config.api_key}\n")
                keys_updated["BINANCE_API_KEY"] = True
            elif line.startswith("BINANCE_API_SECRET="):
                new_lines.append(f"BINANCE_API_SECRET={config.api_secret}\n")
                keys_updated["BINANCE_API_SECRET"] = True
            elif line.startswith("BINANCE_TESTNET="):
                new_lines.append(f"BINANCE_TESTNET={str(config.testnet).lower()}\n")
                keys_updated["BINANCE_TESTNET"] = True
            else:
                new_lines.append(line)
        
        # Append valid missing keys
        if not keys_updated["BINANCE_API_KEY"]:
            new_lines.append(f"BINANCE_API_KEY={config.api_key}\n")
        if not keys_updated["BINANCE_API_SECRET"]:
            new_lines.append(f"BINANCE_API_SECRET={config.api_secret}\n")
        if not keys_updated["BINANCE_TESTNET"]:
            new_lines.append(f"BINANCE_TESTNET={str(config.testnet).lower()}\n")
            
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
            
        logger.info("API Configuration updated and saved to .env")
        
        # 3. Re-initialize Binance Client
        # We need to import main here to avoid circular imports at top level
        import app.main as main_app
        if main_app.binance_client:
            await main_app.binance_client.close()
            # The client reads settings from app.core.config.settings, which we just updated
            await main_app.binance_client.initialize()
            logger.info("Binance Client re-initialized with new settings")
            
        return {"status": "success", "message": "Configuration saved and client reconnected"}

    except Exception as e:
        logger.error(f"Failed to update API config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
