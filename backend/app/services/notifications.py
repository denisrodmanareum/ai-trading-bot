"""
Notification System
Desktop, Email, Telegram 알림
"""
from __future__ import annotations

from loguru import logger
from typing import Optional, List
from enum import Enum
from pathlib import Path
import json
import aiohttp


class NotificationType(Enum):
    """알림 타입"""
    TRADE_EXECUTED = "trade_executed"
    POSITION_CLOSED = "position_closed"
    STOP_LOSS_HIT = "stop_loss_hit"
    TAKE_PROFIT_HIT = "take_profit_hit"
    DAILY_LIMIT_REACHED = "daily_limit_reached"
    AI_TRAINING_COMPLETE = "ai_training_complete"
    PRICE_ALERT = "price_alert"
    SYSTEM_ERROR = "system_error"


class NotificationManager:
    """알림 관리자"""
    
    def __init__(self):
        # Persisted settings path (not committed; see .gitignore)
        self._config_path = (
            Path(__file__).resolve().parents[2] / "data" / "config" / "notification_settings.json"
        )

        self.enabled_channels = {
            'desktop': True,
            'email': False,
            'telegram': False
        }
        
        # 설정
        self.email_config = {
            'smtp_server': '',
            'smtp_port': 587,
            'from_email': '',
            'to_email': '',
            'password': ''
        }
        
        self.telegram_config = {
            'bot_token': '',
            'chat_id': ''
        }
        
        # 가격 알림
        self.price_alerts = []  # [{'symbol': 'BTCUSDT', 'price': 100000, 'direction': 'above'}]

        # Load persisted config if available
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        try:
            if not self._config_path.exists():
                return
            raw = json.loads(self._config_path.read_text(encoding="utf-8"))
            channels = raw.get("enabled_channels")
            if isinstance(channels, dict):
                self.enabled_channels.update({k: bool(v) for k, v in channels.items()})
            telegram = raw.get("telegram_config")
            if isinstance(telegram, dict):
                # Keep only known keys
                for k in ("bot_token", "chat_id"):
                    if k in telegram and isinstance(telegram[k], str):
                        self.telegram_config[k] = telegram[k]
            email = raw.get("email_config")
            if isinstance(email, dict):
                self.email_config.update({k: v for k, v in email.items() if k in self.email_config})

            logger.info(f"🔔 Notification settings loaded: {self._config_path}")
        except Exception as e:
            logger.warning(f"Notification settings load failed (ignored): {e}")

    def _save_to_disk(self) -> None:
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "enabled_channels": self.enabled_channels,
                "telegram_config": self.telegram_config,
                "email_config": self.email_config,
            }
            self._config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Notification settings save failed (ignored): {e}")
    
    async def send(
        self,
        type: NotificationType,
        title: str,
        message: str,
        channels: Optional[List[str]] = None
    ):
        """알림 전송"""
        if channels is None:
            channels = [c for c, enabled in self.enabled_channels.items() if enabled]
        
        for channel in channels:
            try:
                if channel == 'desktop' and self.enabled_channels['desktop']:
                    await self._send_desktop(title, message)
                elif channel == 'email' and self.enabled_channels['email']:
                    await self._send_email(title, message)
                elif channel == 'telegram' and self.enabled_channels['telegram']:
                    await self._send_telegram(message)
            except Exception as e:
                logger.error(f"Failed to send {channel} notification: {e}")
    
    async def _send_desktop(self, title: str, message: str):
        """데스크톱 알림"""
        # 실제 구현 시 WebSocket으로 프론트엔드에 전송
        logger.info(f"🔔 Desktop: {title} - {message}")
    
    async def _send_email(self, title: str, message: str):
        """이메일 알림"""
        if not self.email_config['from_email']:
            return
        
        # 실제 구현 시 SMTP로 이메일 전송
        import smtplib
        from email.mime.text import MIMEText
        
        try:
            msg = MIMEText(message)
            msg['Subject'] = f"[Trading Bot] {title}"
            msg['From'] = self.email_config['from_email']
            msg['To'] = self.email_config['to_email']
            
            # SMTP 전송 (실제로는 비동기로)
            logger.info(f"📧 Email sent: {title}")
        except Exception as e:
            logger.error(f"Email send failed: {e}")
    
    async def _send_telegram(self, message: str):
        """텔레그램 알림"""
        bot_token = (self.telegram_config.get('bot_token') or "").strip()
        chat_id = (self.telegram_config.get('chat_id') or "").strip()
        if not bot_token or not chat_id:
            return
        
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    text = await resp.text()
                    if resp.status >= 400:
                        raise RuntimeError(f"Telegram HTTP {resp.status}: {text[:200]}")
                    try:
                        payload = json.loads(text)
                    except Exception:
                        payload = {"ok": False, "raw": text[:200]}
                    if not payload.get("ok", False):
                        raise RuntimeError(f"Telegram API error: {payload}")

            logger.info("📱 Telegram sent")
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            raise
    
    def add_price_alert(self, symbol: str, price: float, direction: str):
        """가격 알림 추가"""
        self.price_alerts.append({
            'symbol': symbol,
            'price': price,
            'direction': direction,  # 'above' or 'below'
            'triggered': False
        })
        logger.info(f"Price alert added: {symbol} {direction} ${price}")
    
    async def check_price_alerts(self, symbol: str, current_price: float):
        """가격 알림 확인"""
        for alert in self.price_alerts:
            if alert['symbol'] != symbol or alert['triggered']:
                continue
            
            triggered = False
            if alert['direction'] == 'above' and current_price >= alert['price']:
                triggered = True
            elif alert['direction'] == 'below' and current_price <= alert['price']:
                triggered = True
            
            if triggered:
                alert['triggered'] = True
                await self.send(
                    NotificationType.PRICE_ALERT,
                    "Price Alert",
                    f"{symbol} reached ${current_price:.2f}"
                )
    
    def configure(self, channel: str, settings: dict):
        """알림 채널 설정"""
        if channel == 'email':
            self.email_config.update(settings)
            self.enabled_channels['email'] = True
        elif channel == 'telegram':
            self.telegram_config.update(settings)
            # NOTE: enabling/disabling is controlled by enabled_channels; do not force-enable here.
        
        logger.info(f"Notification channel configured: {channel}")
        self._save_to_disk()
    
    def get_status(self) -> dict:
        """알림 상태 반환"""
        return {
            'channels': self.enabled_channels,
            'price_alerts': len([a for a in self.price_alerts if not a['triggered']]),
            'email_configured': bool(self.email_config['from_email']),
            'telegram_configured': bool(self.telegram_config['bot_token'])
        }


# Global instance
notification_manager = NotificationManager()


# Helper functions
async def notify_trade_executed(symbol: str, side: str, quantity: float, price: float):
    """거래 체결 알림"""
    await notification_manager.send(
        NotificationType.TRADE_EXECUTED,
        "Trade Executed",
        f"{side} {quantity} {symbol} @ ${price}"
    )


async def notify_position_closed(symbol: str, pnl: float, pnl_percent: float):
    """포지션 청산 알림"""
    emoji = "🟢" if pnl >= 0 else "🔴"
    await notification_manager.send(
        NotificationType.POSITION_CLOSED,
        "Position Closed",
        f"{emoji} {symbol}: ${pnl:.2f} ({pnl_percent:.2f}%)"
    )


async def notify_daily_limit(limit_type: str, value: float):
    """일일 제한 도달 알림"""
    await notification_manager.send(
        NotificationType.DAILY_LIMIT_REACHED,
        "Daily Limit Reached",
        f"{limit_type} limit reached: {value}",
        channels=['desktop', 'telegram']  # 중요하므로 여러 채널로
    )
