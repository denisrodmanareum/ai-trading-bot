"""
Simplified Binance Futures Client
"""
from binance import AsyncClient
from loguru import logger
import time
from app.core.config import settings
from trading.base_client import BaseExchangeClient

class BinanceClient(BaseExchangeClient):
    """Binance Futures API Client"""
    
    def __init__(self):
        self.client = None
        
    async def initialize(self):
        """Initialize client"""
        try:
            self.client = await AsyncClient.create(
                api_key=settings.BINANCE_API_KEY,
                api_secret=settings.BINANCE_API_SECRET,
                testnet=settings.BINANCE_TESTNET
            )
            
            # Sync server time to avoid -1021 error (Timestamp ahead)
            res = await self.client.get_server_time()
            server_time = res['serverTime']
            local_time = int(time.time() * 1000)
            self.client.timestamp_offset = server_time - local_time
            
            logger.info(f"✅ Binance Client initialized (Time Offset: {self.client.timestamp_offset}ms)")
        except Exception as e:
            logger.error(f"❌ Binance initialization failed: {e}")
            raise
    
    async def close(self):
        """Close connection"""
        if self.client:
            await self.client.close_connection()
    
    async def get_account_info(self):
        """Get account info"""
        await self.ensure_connection()
        account = await self.client.futures_account()
        return {
            "balance": float(account['totalWalletBalance']),
            "unrealized_pnl": float(account['totalUnrealizedProfit']),
            "available_balance": float(account['availableBalance']),
            "maint_margin": float(account['totalMaintMargin']),
            "margin_balance": float(account['totalMarginBalance']),
            "position_initial_margin": float(account['totalPositionInitialMargin']),
            "open_order_initial_margin": float(account['totalOpenOrderInitialMargin']),
            "max_withdraw_amount": float(account['maxWithdrawAmount'])
        }
    
    async def get_current_price(self, symbol="BTCUSDT"):
        """Get current price"""
        await self.ensure_connection()
        ticker = await self.client.futures_symbol_ticker(symbol=symbol)
        return float(ticker['price'])
        
    async def ensure_connection(self):
        """Ensure client session is active"""
        if self.client is None or (hasattr(self.client, 'session') and self.client.session.closed):
            logger.warning("⚠️ Binance client session is closed or missing. Reconnecting...")
            await self.initialize()

    async def get_klines(self, symbol="BTCUSDT", interval="1h", limit=100):
        """Get klines/candles"""
        await self.ensure_connection()
        
        import pandas as pd
        klines = await self.client.futures_klines(
            symbol=symbol,
            interval=interval,
            limit=limit
        )
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        return df

    async def get_raw_klines(self, symbol="BTCUSDT", interval="1m", limit=50):
        """Get raw klines (list of lists) with connection check"""
        await self.ensure_connection()
        return await self.client.futures_klines(
            symbol=symbol,
            interval=interval,
            limit=limit
        )

    async def get_position(self, symbol="BTCUSDT"):
        """Get safe position info for single symbol"""
        try:
            # logger.debug(f"Fetching position for {symbol}...")
            positions = await self.client.futures_position_information(symbol=symbol)
            # logger.debug(f"Raw positions for {symbol}: {positions}")
            
            if positions:
                # Find the specific symbol in case Binance returns more or slightly different list
                pos = next((p for p in positions if p['symbol'] == symbol), positions[0])
                return {
                    "symbol": pos['symbol'],
                    "position_amt": float(pos['positionAmt']),
                    "entry_price": float(pos['entryPrice']),
                    "unrealized_pnl": float(pos['unRealizedProfit']),
                    "leverage": int(pos.get('leverage', 5)),
                    "liquidation_price": float(pos.get('liquidationPrice', 0))
                }
            
            # If empty, return a "null" position instead of None to prevent logical skips
            logger.warning(f"No position record found for {symbol} in Binance response. Returning zero position.")
            return {
                "symbol": symbol,
                "position_amt": 0.0,
                "entry_price": 0.0,
                "unrealized_pnl": 0.0,
                "leverage": 5,
                "liquidation_price": 0.0
            }
        except Exception as e:
            logger.error(f"Failed to get position for {symbol}: {e}")
            raise
    
    async def get_all_positions(self):
        """Get all positions with mark prices"""
        positions = await self.client.futures_position_information()
        active = []
        
        # Collect active positions
        for pos in positions:
            amt = float(pos['positionAmt'])
            if amt != 0:
                active.append({
                    "symbol": pos['symbol'],
                    "position_amt": amt,
                    "entry_price": float(pos['entryPrice']),
                    "unrealized_pnl": float(pos['unRealizedProfit']),
                    "leverage": int(pos.get('leverage', 5)),
                    "mark_price": 0.0  # Will be filled below
                })
        
        # Fetch mark prices for all active symbols
        if active:
            try:
                # Get all mark prices at once
                all_mark_prices = await self.client.futures_mark_price()
                mark_price_map = {item['symbol']: float(item['markPrice']) for item in all_mark_prices}
                
                # Update mark prices for active positions
                for pos in active:
                    pos['mark_price'] = mark_price_map.get(pos['symbol'], 0.0)
            except Exception as e:
                logger.warning(f"Failed to fetch mark prices: {e}")
        
        return active
    
    async def place_market_order(self, symbol, side, quantity, reduce_only=False):
        """Place market order"""
        order = await self.client.futures_create_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=quantity,
            reduceOnly=reduce_only
        )
        logger.info(f"Order placed: {side} {quantity} {symbol} (reduce_only={reduce_only})")
        return order
    
    async def place_stop_market_order(self, symbol, side, quantity, stop_price, reduce_only=False):
        """
        Place stop market order for SL
        
        Args:
            symbol: Trading symbol
            side: "BUY" or "SELL"
            quantity: Order quantity
            stop_price: Stop trigger price
            reduce_only: Reduce only mode
        """
        try:
            order = await self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type="STOP_MARKET",
                quantity=quantity,
                stopPrice=stop_price,
                reduceOnly='true' if reduce_only else 'false'
            )
            logger.info(f"Stop Market Order placed: {side} {quantity} @ {stop_price} {symbol}")
            return order
        except Exception as e:
            logger.error(f"Failed to place stop market order: {e}")
            raise

    async def place_bracket_orders(
        self,
        symbol: str,
        position_side: str,
        quantity: float,
        stop_loss_price: float | None,
        take_profit_price: float | None,
    ) -> dict:
        """
        Place reduce-only SL/TP orders for an open position.
        position_side: "LONG" or "SHORT"
        Returns: {"sl": order|None, "tp": order|None}
        """
        results: dict = {"sl": None, "tp": None}
        if not stop_loss_price and not take_profit_price:
            return results

        # Close side is opposite of entry
        close_side = "SELL" if position_side.upper() == "LONG" else "BUY"

        # Binance Futures uses STOP_MARKET / TAKE_PROFIT_MARKET with stopPrice.
        # closePosition is safer (no qty needed), but some accounts/symbols may reject it.
        # We'll try closePosition=True first, then fallback to reduceOnly+quantity.
        
        async def _round_price(sym: str, prc: float):
            try:
                info = await self.get_exchange_info()
                s_info = next((s for s in info['symbols'] if s['symbol'] == sym), None)
                if not s_info: return round(prc, 2)
                precision = int(s_info.get('pricePrecision', 2))
                return round(prc, precision)
            except:
                return round(prc, 2)

        async def _create(order_type: str, stop_price: float, side: str):
            # Round price first
            stop_price = await _round_price(symbol, stop_price)
            
            # --- SAFETY BUFFER ---
            # To avoid "Order would immediately trigger", ensure stopPrice is on the correct side of current price.
            try:
                ticker = await self.client.futures_symbol_ticker(symbol=symbol)
                current_price = float(ticker['price'])
                
                # Minimum buffer (0.1% for safety)
                buffer = current_price * 0.001 
                
                if order_type == "STOP_MARKET":
                    # For SL:
                    # BUY (to close SHORT): stopPrice must be > current
                    # SELL (to close LONG): stopPrice must be < current
                    if side == "BUY" and stop_price <= current_price:
                        stop_price = current_price + buffer
                        logger.info(f"🛡️ Nudged SL BUY price to {stop_price} (Buffer)")
                    elif side == "SELL" and stop_price >= current_price:
                        stop_price = current_price - buffer
                        logger.info(f"🛡️ Nudged SL SELL price to {stop_price} (Buffer)")
                
                elif order_type == "TAKE_PROFIT_MARKET":
                    # For TP:
                    # BUY (to close SHORT): stopPrice must be < current
                    # SELL (to close LONG): stopPrice must be > current
                    if side == "BUY" and stop_price >= current_price:
                        stop_price = current_price - buffer
                        logger.info(f"🛡️ Nudged TP BUY price to {stop_price} (Buffer)")
                    elif side == "SELL" and stop_price <= current_price:
                        stop_price = current_price + buffer
                        logger.info(f"🛡️ Nudged TP SELL price to {stop_price} (Buffer)")
                
                # Re-round after buffer
                stop_price = await _round_price(symbol, stop_price)
            except Exception as e:
                logger.warning(f"Safety buffer check failed: {e}")

            try:
                return await self.client.futures_create_order(
                    symbol=symbol,
                    side=side, # Use side passed to _create
                    type=order_type,
                    stopPrice=stop_price,
                    closePosition=True,
                    workingType="MARK_PRICE",
                )
            except Exception as e:
                # If closePosition fails (e.g. parameter conflict), fallback to reduceOnly+qty
                logger.warning(f"Bracket {order_type} closePosition failed, fallback qty: {e}")
                return await self.client.futures_create_order(
                    symbol=symbol,
                    side=side,
                    type=order_type,
                    stopPrice=stop_price,
                    quantity=quantity,
                    reduceOnly=True,
                    workingType="MARK_PRICE",
                )

        try:
            if stop_loss_price:
                results["sl"] = await _create("STOP_MARKET", float(stop_loss_price), close_side)
                logger.info(f"Placed SL ({symbol}) @ {stop_loss_price}")
        except Exception as e:
            logger.error(f"Failed to place SL for {symbol}: {e}")

        try:
            if take_profit_price:
                results["tp"] = await _create("TAKE_PROFIT_MARKET", float(take_profit_price), close_side)
                logger.info(f"Placed TP ({symbol}) @ {take_profit_price}")
        except Exception as e:
            logger.error(f"Failed to place TP for {symbol}: {e}")

        return results

    async def cancel_open_orders(self, symbol: str) -> int:
        """Cancel all open orders for symbol. Returns cancelled count."""
        try:
            orders = await self.get_open_orders(symbol=symbol)
            cancelled = 0
            for o in orders:
                try:
                    await self.cancel_order(symbol=symbol, order_id=o.get("orderId"))
                    cancelled += 1
                except Exception as e:
                    logger.warning(f"Cancel order failed ({symbol}): {e}")
            return cancelled
        except Exception as e:
            logger.error(f"Cancel open orders failed ({symbol}): {e}")
            return 0

    async def get_funding_rate(self, symbol="BTCUSDT"):
        """Get funding rate"""
        try:
            funding = await self.client.futures_funding_rate(symbol=symbol, limit=1)
            if funding:
                return float(funding[-1]['fundingRate'])
            return 0.0
        except Exception as e:
            logger.error(f"Failed to get funding rate: {e}")
            return 0.0

    async def change_leverage(self, symbol="BTCUSDT", leverage=5):
        """Change leverage for symbol"""
        try:
            return await self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
        except Exception as e:
            # Leverage change can fail if position exists - not critical
            logger.debug(f"Leverage change skipped for {symbol}: {e}")
            return None  # Return None instead of raising, let caller handle it

    async def get_order_book(self, symbol="BTCUSDT", limit=10):
        """Get order book depth"""
        try:
            depth = await self.client.futures_order_book(symbol=symbol, limit=limit)
            return {
                "symbol": symbol,
                "bids": depth['bids'], # List of [price, qty]
                "asks": depth['asks']  # List of [price, qty]
            }
        except Exception as e:
            logger.error(f"Failed to get order book: {e}")
            return {"bids": [], "asks": []}

    async def get_ticker(self, symbol: str):
        """Get ticker price"""
        try:
            ticker = await self.client.futures_symbol_ticker(symbol=symbol)
            return {
                'symbol': ticker['symbol'],
                'price': float(ticker['price']),
                'bidPrice': float(ticker.get('bidPrice', ticker['price'])),
                'askPrice': float(ticker.get('askPrice', ticker['price']))
            }
        except Exception as e:
            logger.error(f"Failed to get ticker for {symbol}: {e}")
            return {'symbol': symbol, 'price': 0, 'bidPrice': 0, 'askPrice': 0}
    
    async def get_orderbook(self, symbol: str, limit: int = 20):
        """Get order book"""
        try:
            orderbook = await self.client.futures_order_book(symbol=symbol, limit=limit)
            return {
                'symbol': symbol,
                'bids': orderbook['bids'],
                'asks': orderbook['asks']
            }
        except Exception as e:
            logger.error(f"Failed to get orderbook for {symbol}: {e}")
            return {'symbol': symbol, 'bids': [], 'asks': []}
    
    async def place_limit_order(self, symbol, side, quantity, price, time_in_force='GTC', reduce_only=False):
        """Place limit order"""
        try:
            params = {
                'symbol': symbol,
                'side': side,
                'type': 'LIMIT',
                'timeInForce': time_in_force,
                'quantity': quantity,
                'price': price
            }
            if reduce_only:
                params['reduceOnly'] = 'true'
            
            order = await self.client.futures_create_order(**params)
            logger.info(f"Limit Order placed: {side} {quantity} @ {price} {symbol}")
            return order
        except Exception as e:
            logger.error(f"Failed to place limit order: {e}")
            raise
    
    async def get_orderbook(self, symbol: str, limit: int = 20):
        """Alias for get_order_book (for compatibility)"""
        return await self.get_order_book(symbol, limit)

    async def get_open_orders(self, symbol="BTCUSDT"):
        """Get open orders"""
        try:
            return await self.client.futures_get_open_orders(symbol=symbol)
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            return []

    async def cancel_order(self, symbol, order_id):
        """Cancel specific order"""
        try:
            return await self.client.futures_cancel_order(symbol=symbol, orderId=order_id)
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            raise

    async def get_user_trades(self, symbol: str = "BTCUSDT", limit: int = 50) -> List[Dict]:
        """Get user trade history with PnL (Standardized)"""
        try:
            await self.ensure_connection()
            trades = await self.client.futures_account_trades(symbol=symbol, limit=limit)
            return [{
                "symbol": t['symbol'],
                "price": float(t['price']),
                "qty": float(t['qty']),
                "pnl": float(t['realizedPnl']),
                "commission": float(t['commission']),
                "side": t['side'],
                "time": int(t['time'])
            } for t in trades]
        except Exception as e:
            logger.error(f"Failed to get user trades: {e}")
            return []
    
    async def get_exchange_info(self):
        """Get exchange trading rules and symbol information"""
        try:
            info = await self.client.futures_exchange_info()
            return info
        except Exception as e:
            logger.error(f"Failed to get exchange info: {e}")
            return {"symbols": []}

    async def get_mark_price(self, symbol: str) -> float:
        """Get mark price for symbol"""
        try:
            await self.ensure_connection()
            res = await self.client.futures_mark_price(symbol=symbol)
            return float(res['markPrice'])
        except Exception as e:
            logger.error(f"Failed to get mark price for {symbol}: {e}")
            return 0.0

    async def get_mark_price_info(self, symbol: str) -> Dict:
        """Get comprehensive mark price info"""
        try:
            await self.ensure_connection()
            res = await self.client.futures_mark_price(symbol=symbol)
            return {
                "mark_price": float(res['markPrice']),
                "index_price": float(res['indexPrice']),
                "next_funding_time": int(res['nextFundingTime'])
            }
        except Exception as e:
            logger.error(f"Failed to get mark price info for {symbol}: {e}")
            return {"mark_price": 0, "index_price": 0, "next_funding_time": 0}

    async def get_24h_ticker(self, symbol: str) -> Dict:
        """Get 24h ticker data"""
        try:
            await self.ensure_connection()
            res = await self.client.futures_ticker(symbol=symbol)
            return {
                "high_24h": float(res['highPrice']),
                "low_24h": float(res['lowPrice']),
                "volume_24h": float(res['volume'])
            }
        except Exception as e:
            logger.error(f"Failed to get 24h ticker for {symbol}: {e}")
            return {"high_24h": 0, "low_24h": 0, "volume_24h": 0}

    async def get_recent_trades(self, symbol: str, limit: int = 30) -> List[Dict]:
        """Get recent market trades"""
        try:
            await self.ensure_connection()
            trades = await self.client.futures_recent_trades(symbol=symbol, limit=limit)
            return [{
                "id": t['id'],
                "price": t['price'],
                "qty": t['qty'],
                "time": t['time'],
                "is_buyer_maker": t['isBuyerMaker']
            } for t in trades]
        except Exception as e:
            logger.error(f"Failed to get recent trades for {symbol}: {e}")
            return []

