"""
Real-time Price Stream Service
"""
import asyncio
import json
from typing import Optional
from binance import AsyncClient, BinanceSocketManager
from loguru import logger

from trading.binance_client import BinanceClient
from app.services.websocket_manager import WebSocketManager


class PriceStreamService:
    """Streams real-time price data from Binance and broadcasts to WebSocket clients"""
    
    def __init__(self, binance_client: BinanceClient, ws_manager: WebSocketManager):
        self.binance_client = binance_client
        self.ws_manager = ws_manager
        self.bm: Optional[BinanceSocketManager] = None
        self.running = False
        self.symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]  # Expanded for multi-coin support
        self.callbacks = []
        
    def add_callback(self, callback):
        """Add callback for price updates"""
        self.callbacks.append(callback)
        
    async def start(self):
        """Start price streaming"""
        if self.running:
            logger.warning("Price stream already running")
            return
        
        self.running = True
        logger.info("Starting price stream service...")
        
        try:
            # Create Binance Socket Manager
            self.bm = BinanceSocketManager(self.binance_client.client)
            
            # Start streams for each symbol
            for symbol in self.symbols:
                asyncio.create_task(self._stream_symbol(symbol))
            
            logger.info(f"Price streams started for {self.symbols}")
            
        except Exception as e:
            logger.error(f"Failed to start price stream: {e}")
            self.running = False
    
    async def stop(self):
        """Stop price streaming"""
        self.running = False
        # bm does not need closing, it uses the client
        logger.info("Price stream service stopped")
    
    async def _stream_symbol(self, symbol: str):
        """Stream real-time data for a specific symbol"""
        logger.info(f"Starting stream for {symbol}")
        
        # Kline (candlestick) stream
        async with self.bm.kline_socket(symbol, interval='1m') as stream:
            while self.running:
                try:
                    msg = await stream.recv()
                    await self._process_kline(msg)
                except Exception as e:
                    logger.error(f"Stream error for {symbol}: {e}")
                    await asyncio.sleep(5)  # Wait before reconnecting
    
    async def _process_kline(self, msg: dict):
        """Process kline data and broadcast"""
        try:
            if msg['e'] == 'kline':
                kline = msg['k']
                
                data = {
                    "type": "kline",
                    "symbol": kline['s'],
                    "timestamp": kline['t'],
                    "open": float(kline['o']),
                    "high": float(kline['h']),
                    "low": float(kline['l']),
                    "close": float(kline['c']),
                    "volume": float(kline['v']),
                    "is_closed": kline['x']
                }
                
                # Broadcast to WebSocket clients
                await self.ws_manager.broadcast(data, channel="prices")
                
                if kline['x']: # If candle closed
                    asyncio.create_task(self._save_candle_to_db(kline))

                # Notify internal callbacks
                for callback in self.callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(data)
                        else:
                            callback(data)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
                
        except Exception as e:
            logger.error(f"Failed to process kline: {e}")

    async def _save_candle_to_db(self, kline: dict):
        """Save closed candle to database asynchronously"""
        try:
            from app.database import SessionLocal
            from app.models import Candle
            from datetime import datetime
            
            # Convert timestamp (ms) to datetime
            ts = datetime.fromtimestamp(kline['t'] / 1000.0)
            
            async with SessionLocal() as session:
                candle = Candle(
                    symbol=kline['s'],
                    interval='1m', # Hardcoded for now, stream is 1m
                    timestamp=ts,
                    open=float(kline['o']),
                    high=float(kline['h']),
                    low=float(kline['l']),
                    close=float(kline['c']),
                    volume=float(kline['v'])
                )
                session.add(candle)
                await session.commit()
                # logger.debug(f"Saved candle {kline['s']} @ {ts}")
                
        except Exception as e:
            logger.error(f"Failed to save candle to DB: {e}")
    
    async def add_symbol(self, symbol: str):
        """Add new symbol to stream"""
        if symbol not in self.symbols:
            self.symbols.append(symbol)
            if self.running:
                asyncio.create_task(self._stream_symbol(symbol))
            logger.info(f"Added {symbol} to price stream")
    
    async def remove_symbol(self, symbol: str):
        """Remove symbol from stream"""
        if symbol in self.symbols:
            self.symbols.remove(symbol)
            logger.info(f"Removed {symbol} from price stream")
