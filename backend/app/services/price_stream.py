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
        # 🔧 FIX: Expanded default symbols for better coverage
        self.symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT"]
        self.callbacks = []
        self._symbol_streams = {}  # Track active streams
        
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
            
            # 🔧 FIX: Get initial symbols from coin_selector
            from app.services.coin_selector import coin_selector
            try:
                selected = await coin_selector.get_selected_coins()
                if selected:
                    # Use selected coins, but keep our defaults as fallback
                    self.symbols = list(set(self.symbols + selected))
                    logger.info(f"📊 Using coin selector: {selected}")
            except Exception as e:
                logger.warning(f"Failed to get coin selector list, using defaults: {e}")
            
            # Start streams for each symbol
            for symbol in self.symbols:
                task = asyncio.create_task(self._stream_symbol(symbol))
                self._symbol_streams[symbol] = task
            
            # 🔧 FALLBACK: Start polling loop as backup
            asyncio.create_task(self._polling_loop())
            
            logger.info(f"✅ Price streams started for {len(self.symbols)} symbols: {self.symbols}")
            
        except Exception as e:
            logger.error(f"Failed to start price stream: {e}")
            self.running = False
    
    async def stop(self):
        """Stop price streaming"""
        self.running = False
        
        # Cancel all active stream tasks
        for symbol, task in self._symbol_streams.items():
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.debug(f"Stream cleanup exception for {symbol}: {e}")
        
        self._symbol_streams.clear()
        
        # Close socket manager if exists
        if self.bm:
            try:
                await self.bm.close()
            except Exception as e:
                logger.debug(f"BinanceSocketManager close exception (safe to ignore): {e}")
        
        logger.info("Price stream service stopped")
    
    async def _stream_symbol(self, symbol: str):
        """Stream real-time data for a specific symbol"""
        logger.info(f"Starting stream for {symbol}")
        
        # Kline (candlestick) stream
        try:
            async with self.bm.kline_socket(symbol, interval='1m') as stream:
                logger.info(f"📡 WebSocket connected for {symbol}")
                while self.running:
                    try:
                        # Wait for message with timeout
                        msg = await asyncio.wait_for(stream.recv(), timeout=30)
                        await self._process_kline(msg)
                    except asyncio.TimeoutError:
                        logger.debug(f"WebSocket silent for {symbol} (using polling fallback)")
                        # No need to reconnect yet, just let it loop and try recv again
                        # The polling fallback will cover this period
                    except Exception as e:
                        logger.error(f"Stream error for {symbol}: {e}")
                        await asyncio.sleep(5)  # Wait before reconnecting
        except Exception as e:
            logger.error(f"Failed to open kline socket for {symbol}: {e}")
    
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
                # logger.debug(f"Processing kline for {data['symbol']} (closed: {data['is_closed']})")
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
    
    async def _polling_loop(self):
        """Fallback polling loop if WebSocket is silent"""
        logger.info("📡 Starting fallback polling loop (every 10s)")
        while self.running:
            try:
                # Poll all active symbols as fallback
                current_symbols = list(self.symbols) 
                for symbol in current_symbols:
                    if not self.running: break
                    
                    # Fetch latest 1m kline manually
                    try:
                        klines = await self.binance_client.client.futures_klines(symbol=symbol, interval='1m', limit=2)
                        if klines:
                            k = klines[-1]
                            data = {
                                "type": "kline",
                                "symbol": symbol,
                                "timestamp": k[0],
                                "open": float(k[1]),
                                "high": float(k[2]),
                                "low": float(k[3]),
                                "close": float(k[4]),
                                "volume": float(k[5]),
                                "is_closed": True
                            }
                            
                            for callback in self.callbacks:
                                try:
                                    if asyncio.iscoroutinefunction(callback):
                                        await callback(data)
                                    else:
                                        callback(data)
                                except: pass
                    except Exception as e:
                        logger.debug(f"Polling failed for {symbol}: {e}")

                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Polling loop error: {e}")
                await asyncio.sleep(10)

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
