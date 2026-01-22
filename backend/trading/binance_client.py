"""
Simplified Binance Futures Client
"""
from binance import AsyncClient
from loguru import logger
from app.core.config import settings


class BinanceClient:
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
            logger.info("✅ Binance Client initialized")
        except Exception as e:
            logger.error(f"❌ Binance initialization failed: {e}")
            raise
    
    async def close(self):
        """Close connection"""
        if self.client:
            await self.client.close_connection()
    
    async def get_account_info(self):
        """Get account info"""
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
        ticker = await self.client.futures_symbol_ticker(symbol=symbol)
        return float(ticker['price'])
        
    async def get_klines(self, symbol="BTCUSDT", interval="1h", limit=100):
        """Get klines/candles"""
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
        """Get all positions"""
        positions = await self.client.futures_position_information()
        active = []
        for pos in positions:
            amt = float(pos['positionAmt'])
            if amt != 0:
                active.append({
                    "symbol": pos['symbol'],
                    "position_amt": amt,
                    "entry_price": float(pos['entryPrice']),
                    "unrealized_pnl": float(pos['unRealizedProfit']),
                    "leverage": int(pos.get('leverage', 5))
                })
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

    async def place_limit_order(self, symbol, side, quantity, price):
        """Place limit order"""
        try:
            order = await self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type="LIMIT",
                timeInForce="GTC", # Good Till Cancel
                quantity=quantity,
                price=price
            )
            logger.info(f"Limit Order placed: {side} {quantity} @ {price} {symbol}")
            return order
        except Exception as e:
            logger.error(f"Failed to place limit order: {e}")
            raise

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

    async def get_user_trades(self, symbol="BTCUSDT", limit=50):
        """Get user trade history with PnL"""
        try:
            return await self.client.futures_account_trades(symbol=symbol, limit=limit)
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

