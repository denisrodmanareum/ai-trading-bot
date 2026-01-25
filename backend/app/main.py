"""
Main FastAPI Application
"""
import sys
import asyncio

# 🔧 FIX: Windows ProactorEventLoop issues with pycares/aiohttp
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
from pathlib import Path

from trading.exchange_factory import ExchangeFactory
from app.core.config import settings
from app.services.websocket_manager import WebSocketManager
from app.services.price_stream import PriceStreamService
from app.services.auto_trading import AutoTradingService

# Global client
exchange_client = None
ws_manager = WebSocketManager()
price_service = None
auto_trading_service = None
reporter_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan"""
    global exchange_client, price_service, auto_trading_service, reporter_service
    
    # Startup
    logger.info("Starting AI Trading Bot...")
    
    try:
        from app.database import init_db
        await init_db()
        logger.info("Database initialized")

        exchange_client = await ExchangeFactory.get_client()
        logger.info(f"{settings.ACTIVE_EXCHANGE} client initialized")
        
        # Initialize Price Stream Service
        price_service = PriceStreamService(exchange_client, ws_manager)
        
        # Initialize Auto Trading Service
        auto_trading_service = AutoTradingService(exchange_client, ws_manager)
        
        # Start Auto Trading Service Automaticaly (Delayed to prevent blocking startup)
        import asyncio
        async def start_trading_delayed():
            logger.info("Scheduling Auto Trading start in 10 seconds...")
            await asyncio.sleep(10)
            await auto_trading_service.start()
            
            # --- STARTUP NOTIFICATION ---
            try:
                # 1. Get Model Name
                model_name = "Unknown"
                if auto_trading_service.agent and auto_trading_service.agent.model_path:
                   model_name = Path(auto_trading_service.agent.model_path).name
                elif settings.AI_MODEL_PATH: # Fallback to latest in dir
                   try:
                       import os
                       models = [f for f in os.listdir(settings.AI_MODEL_PATH) if f.endswith('.zip')]
                       if models:
                           model_name = sorted(models)[-1]
                       else:
                           model_name = "Initial Model (New)"
                   except:
                       pass

                # 2. Get Account Info
                account = await exchange_client.get_account_info()
                balance = account.get('balance', 0.0)
                unrealized_pnl = account.get('unrealized_pnl', 0.0)
                pnl_percent = 0.0
                if balance > 0:
                    pnl_percent = (unrealized_pnl / balance) * 100

                # 3. Get Positions
                positions = await exchange_client.get_all_positions()
                
                # 4. Get Public IP (Best effort)
                import socket
                import urllib.request
                try:
                    external_ip = urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
                except:
                    external_ip = "Unknown (Network Error)"
                
                host_info = f"{socket.gethostname()} ({external_ip})"

                # 5. Send Notification
                from app.services.notifications import notify_startup
                await notify_startup(
                    model_name=model_name,
                    ip_address=host_info,
                    balance=balance,
                    unrealized_pnl=unrealized_pnl,
                    pnl_percent=pnl_percent,
                    active_positions=positions
                )
                logger.info("✅ Startup notification sent")
            except Exception as e:
                logger.error(f"Failed to send startup notification: {e}")
            # ----------------------------
            
        asyncio.create_task(start_trading_delayed())
        
        # Register Auto Trading as callback for Price Stream
        price_service.add_callback(auto_trading_service.process_market_data)
        
        # Start Price Stream
        asyncio.create_task(price_service.start())
        
        # Initialize Reporter Service
        from app.services.reporter import DailyReporterService
        reporter_service = DailyReporterService()
        asyncio.create_task(reporter_service.schedule_daily())
        
        logger.info("Price Stream, Auto Trading, Scheduler & Reporter Services started")
        
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
    
    try:
        yield
    except asyncio.CancelledError:
        pass
    
    # Shutdown
    logger.info("Shutting down...")
    
    # Stop services in reverse order
    if auto_trading_service:
        await auto_trading_service.stop()
    
    if price_service:
        await price_service.stop()
    
    # Close all WebSocket connections
    if ws_manager:
        await ws_manager.disconnect_all()
    
    # Close Binance client
    if exchange_client:
        await exchange_client.close()
    
    logger.info("✅ Shutdown complete")


# Create app
app = FastAPI(
    title="AI Trading Bot",
    version="2.0.0",
    lifespan=lifespan
)

# DEBUG: Print all routes on startup
@app.on_event("startup")
async def startup_event():
    logger.info("--- REGISTERED ROUTES ---")
    for route in app.routes:
        logger.info(f"Route: {route.path}")
    logger.info("-------------------------")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "binance": exchange_client is not None
    }


# Import and register routers AFTER app creation
from app.api import dashboard, trading, positions, ai_control, history, ai_analysis, quick_wins, advanced_data, dashboard_v2, coin_selection, settings, webhook

app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(dashboard_v2.router, prefix="/api/dashboard", tags=["Dashboard V2"])
app.include_router(trading.router, prefix="/api/trading", tags=["Trading"])
app.include_router(positions.router, prefix="/api/positions", tags=["Positions"])
app.include_router(ai_control.router, prefix="/api/ai", tags=["AI Control"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(coin_selection.router, prefix="/api/coins", tags=["Coin Selection"])
app.include_router(history.router, prefix="/api/history", tags=["History"])
app.include_router(ai_analysis.router, tags=["AI Analysis"])
app.include_router(quick_wins.router, prefix="/api", tags=["Quick Wins"])
app.include_router(advanced_data.router, prefix="/api", tags=["Advanced Data"])
app.include_router(webhook.router, prefix="/api/webhook", tags=["Webhook"])  # 🆕


@app.get("/api/direct/recent-trades")
async def get_recent_trades_direct(symbol: str = "BTCUSDT", limit: int = 30):
    if exchange_client is None:
        return []
    try:
        trades = await exchange_client.client.futures_recent_trades(symbol=symbol, limit=limit)
        return [{
            "id": t['id'],
            "price": t['price'],
            "qty": t['qty'],
            "time": t['time'],
            "is_buyer_maker": t['isBuyerMaker']
        } for t in trades]
    except Exception as e:
        logger.error(f"Direct trade fetch failed: {e}")
        return []


if __name__ == "__main__":
    import uvicorn
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        pass