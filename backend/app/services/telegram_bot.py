import asyncio
import time
import aiohttp
import json
from loguru import logger
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

from app.services.notifications import notification_manager, NotificationType

class TelegramBotService:
    """
    Telegram Bot Service for interactive commands and periodic reports.
    - Periodic report every 30 minutes
    - Interactive commands: /status, /balance, /positions, /help
    """
    
    def __init__(self, exchange_client, auto_trading_service):
        self.exchange_client = exchange_client
        self.auto_trading_service = auto_trading_service
        self.running = False
        self._report_task: Optional[asyncio.Task] = None
        self._polling_task: Optional[asyncio.Task] = None
        self.last_update_id = 0
        self.report_interval = 30 * 60  # 30 minutes
        
    async def start(self):
        """Start the service"""
        if self.running:
            return
            
        # Check if telegram is configured
        config = notification_manager.telegram_config
        if not config.get('bot_token') or not config.get('chat_id'):
            logger.warning("⚠️ Telegram Bot not started: Token or Chat ID not configured")
            return
            
        self.running = True
        self._report_task = asyncio.create_task(self._report_loop())
        self._polling_task = asyncio.create_task(self._polling_loop())
        logger.info("✅ Telegram Bot Service started")
        
        # Send initial status
        await self.send_status_report(reason="Bot Service Monitoring Started")

    async def stop(self):
        """Stop the service"""
        self.running = False
        if self._report_task:
            self._report_task.cancel()
        if self._polling_task:
            self._polling_task.cancel()
        logger.info("🛑 Telegram Bot Service stopped")

    async def _report_loop(self):
        """Periodic status report loop"""
        try:
            while self.running:
                await asyncio.sleep(self.report_interval)
                if not self.running:
                    break
                
                if notification_manager.enabled_channels.get("telegram", False):
                    await self.send_status_report(reason="Periodic 30m Report")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Telegram report loop error: {e}")

    async def _polling_loop(self):
        """Poll for user commands"""
        bot_token = notification_manager.telegram_config.get('bot_token')
        if not bot_token:
            return
            
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        
        while self.running:
            try:
                params = {
                    "offset": self.last_update_id + 1,
                    "timeout": 30
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params, timeout=40) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("ok"):
                                for update in data.get("result", []):
                                    self.last_update_id = update["update_id"]
                                    if "message" in update and "text" in update["message"]:
                                        await self._handle_command(update["message"])
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Telegram polling error: {e}")
                await asyncio.sleep(10) # Cooling off

    async def _handle_command(self, message: Dict):
        """Handle incoming telegram commands"""
        chat_id = str(message["chat"]["id"])
        allowed_chat_id = str(notification_manager.telegram_config.get('chat_id'))
        
        if chat_id != allowed_chat_id:
            logger.warning(f"Unauthorized telegram command from chat_id: {chat_id}")
            return

        text = message.get("text", "").strip().lower()
        
        if text.startswith("/start") or text.startswith("/help"):
            await self._send_reply(
                "🤖 <b>AI Trading Bot Help</b>\n\n"
                "/status - 현재 통합 상태 보고\n"
                "/balance - 잔고 및 계좌 정보\n"
                "/positions - 활성 포지션 상세\n"
                "/help - 도움말"
            )
        elif text.startswith("/status"):
            await self.send_status_report(reason="User Request")
        elif text.startswith("/balance"):
            await self._send_balance_report()
        elif text.startswith("/positions"):
            await self._send_positions_report()
        else:
            # Silent ignore or friendly message for unknown commands
            pass

    async def send_status_report(self, reason: str = ""):
        """Send a comprehensive status report"""
        try:
            # 1. Account Info
            account = await self.exchange_client.get_account_info()
            balance = account.get('balance', 0.0)
            u_pnl = account.get('unrealized_pnl', 0.0)
            
            # 2. Positions
            positions = await self.exchange_client.get_all_positions()
            
            # 3. Bot State
            mode = self.auto_trading_service.strategy_config.mode
            interval = self.auto_trading_service.strategy_config.selected_interval
            status = "RUNNING" if self.auto_trading_service.running else "STOPPED"
            
            # 4. Format Message
            emoji = "✅" if status == "RUNNING" else "🛑"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            msg = (
                f"{emoji} <b>[Bot Status Report]</b>\n"
                f"🕒 시간: <code>{timestamp}</code>\n"
                f"📝 사유: <code>{reason}</code>\n\n"
                f"🤖 <b>시스템 상태:</b>\n"
                f"• 상태: <b>{status}</b>\n"
                f"• 모드: <b>{mode}</b> | 타임프레임: <b>{interval}</b>\n"
                f"• 하이브리드: <b>{'ON (PPO+LSTM)' if self.auto_trading_service.hybrid_ai.mode == 'full_hybrid' else 'OFF (PPO Only)'}</b>\n\n"
                f"💰 <b>계좌 요약:</b>\n"
                f"• 잔고: <b>{self._fmt_usdt(balance)}</b> USDT\n"
                f"• 미실현손익: <b>{u_pnl:+.2f}</b> USDT\n\n"
            )
            
            if positions:
                msg += "📊 <b>활성 포지션:</b>\n"
                for p in positions:
                    sym = p['symbol']
                    amt = float(p['position_amt'])
                    side = "LONG" if amt > 0 else "SHORT"
                    entry_price = float(p['entry_price'])
                    mark_price = float(p.get('mark_price', 0))
                    pnl = float(p['unrealized_pnl'])
                    
                    # ROE Calculation
                    leverage = int(p.get('leverage', 1))
                    roe = (pnl / (abs(amt) * entry_price / leverage)) * 100 if entry_price > 0 else 0
                    
                    # Bracket info (TP/SL)
                    bracket = self.auto_trading_service.brackets.get(sym, {})
                    tp = bracket.get('tp', 'None')
                    sl = bracket.get('sl', 'None')
                    
                    pnl_emoji = "🟢" if pnl >= 0 else "🔴"
                    msg += (
                        f"• {sym} ({side} {leverage}x)\n"
                        f"  └ PnL: {pnl_emoji} <b>{pnl:+.2f} ({roe:+.2f}%)</b>\n"
                        f"  └ Entry: {self._fmt_usdt(entry_price)} | Mark: {self._fmt_usdt(mark_price)}\n"
                        f"  └ TP: <code>{tp}</code> | SL: <code>{sl}</code>\n"
                    )
            else:
                msg += "📊 <b>포지션:</b> 현재 없음 (Flat)\n"
                
            await self._send_reply(msg)
            
        except Exception as e:
            logger.error(f"Failed to send status report: {e}")

    async def _send_balance_report(self):
        """Send specific balance report"""
        try:
            account = await self.exchange_client.get_account_info()
            bal = account.get('balance', 0.0)
            avail = account.get('available_balance', 0.0)
            u_pnl = account.get('unrealized_pnl', 0.0)
            
            msg = (
                "💰 <b>[Account Balance]</b>\n\n"
                f"• 총 잔고: <b>{self._fmt_usdt(bal)}</b> USDT\n"
                f"• 비실현손익: <b>{u_pnl:+.2f}</b> USDT\n"
                f"• 가용 잔고: <b>{self._fmt_usdt(avail)}</b> USDT\n"
            )
            await self._send_reply(msg)
        except Exception as e:
            logger.error(f"Balance report error: {e}")

    async def _send_positions_report(self):
        """Send specific positions report (more detail)"""
        try:
            positions = await self.exchange_client.get_all_positions()
            if not positions:
                await self._send_reply("📊 현재 활성 포지션이 없습니다.")
                return
                
            msg = "📊 <b>[Detailed Positions]</b>\n\n"
            for p in positions:
                sym = p['symbol']
                amt = float(p['position_amt'])
                side = "LONG" if amt > 0 else "SHORT"
                entry = float(p['entry_price'])
                mark = float(p.get('mark_price', 0))
                pnl = float(p['unrealized_pnl'])
                lev = int(p.get('leverage', 1))
                roe = (pnl / (abs(amt) * entry / lev)) * 100 if entry > 0 else 0
                
                bracket = self.auto_trading_service.brackets.get(sym, {})
                tp = bracket.get('tp', 'None')
                sl = bracket.get('sl', 'None')
                
                pnl_emoji = "🟢" if pnl >= 0 else "🔴"
                msg += (
                    f"<b>{sym} {side} ({lev}x)</b>\n"
                    f"포지션: {abs(amt):.4f} {sym}\n"
                    f"PnL: {pnl_emoji} <b>{pnl:+.2f} USDT ({roe:+.2f}%)</b>\n"
                    f"Entry: {entry:,.2f} -> Mark: {mark:,.2f}\n"
                    f"🎯 TP: <code>{tp}</code>\n"
                    f"🛑 SL: <code>{sl}</code>\n\n"
                )
            await self._send_reply(msg)
        except Exception as e:
            logger.error(f"Positions report error: {e}")

    async def _send_reply(self, text: str):
        """Helper to send telegram message"""
        try:
            await notification_manager.send(
                NotificationType.PRICE_ALERT, # Use generic type
                "Telegram Command Reply",
                text,
                channels=["telegram"]
            )
        except Exception as e:
            logger.error(f"Reply send failed: {e}")

    def _fmt_usdt(self, x: float) -> str:
        """Format number to USDT string"""
        try:
            if x < 0.1: return f"{x:.5f}"
            if x < 1: return f"{x:.4f}"
            if x < 10: return f"{x:.3f}"
            return f"{x:,.2f}"
        except:
            return str(x)
