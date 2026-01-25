"""
Bybit Futures Client implementation
"""
import aiohttp
import hmac
import hashlib
import time
import pandas as pd
from typing import Dict, List, Optional
from loguru import logger
from app.core.config import settings
from trading.base_client import BaseExchangeClient

class BybitClient(BaseExchangeClient):
    """Bybit V5 API Client implementation"""
    
    def __init__(self):
        self.api_key = settings.BYBIT_API_KEY
        self.api_secret = settings.BYBIT_API_SECRET
        self.testnet = settings.BYBIT_TESTNET
        self.base_url = "https://api-testnet.bybit.com" if self.testnet else "https://api.bybit.com"
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self):
        """Initialize session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        logger.info(f"✅ Bybit Client initialized (Testnet: {self.testnet})")
        
    async def close(self):
        """Close session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _request(self, method: str, path: str, params: Optional[Dict] = None, signed: bool = False) -> Dict:
        """Helper to make signed/unsigned requests"""
        if self.session is None or self.session.closed:
            await self.initialize()
            
        url = f"{self.base_url}{path}"
        headers = {}
        
        if signed:
            timestamp = str(int(time.time() * 1000))
            recv_window = "5000"
            
            # Simple signature generation for Bybit V5
            if method == "GET":
                query_str = "&".join([f"{k}={v}" for k, v in sorted(params.items())]) if params else ""
                param_str = query_str
            else:
                import json
                param_str = json.dumps(params) if params else ""
                
            raw_data = timestamp + self.api_key + recv_window + param_str
            signature = hmac.new(
                self.api_secret.encode("utf-8"),
                raw_data.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()
            
            headers = {
                "X-BSRV-API-KEY": self.api_key,
                "X-BSRV-SIGN": signature,
                "X-BSRV-TIMESTAMP": timestamp,
                "X-BSRV-RECV-WINDOW": recv_window,
                "Content-Type": "application/json"
            }

        try:
            async with self.session.request(method, url, params=params if method == "GET" else None, json=params if method != "GET" else None, headers=headers) as resp:
                data = await resp.json()
                if data.get("retCode") != 0:
                    logger.error(f"Bybit API Error: {data.get('retMsg')} (Code: {data.get('retCode')})")
                return data
        except Exception as e:
            logger.error(f"Bybit Request Failed: {e}")
            raise

    async def get_account_info(self) -> Dict:
        """Get Unified Account balance (simplified)"""
        # path: /v5/account/wallet-balance
        resp = await self._request("GET", "/v5/account/wallet-balance", {"accountType": "UNIFIED"}, signed=True)
        if resp.get("retCode") == 0:
            result = resp["result"]["list"][0]
            # Map Bybit fields to base interface
            return {
                "balance": float(result.get("totalWalletBalance", 0)),
                "unrealized_pnl": float(result.get("totalUnrealizedPnl", 0)),
                "available_balance": float(result.get("totalAvailableBalance", 0))
            }
        return {"balance": 0, "unrealized_pnl": 0, "available_balance": 0}

    async def get_current_price(self, symbol: str) -> float:
        """Get ticker price"""
        resp = await self._request("GET", "/v5/market/tickers", {"category": "linear", "symbol": symbol})
        if resp.get("retCode") == 0:
            return float(resp["result"]["list"][0]["lastPrice"])
        return 0.0

    async def get_klines(self, symbol: str, interval: str, limit: int = 100) -> pd.DataFrame:
        """Get klines"""
        # Map intervals from Binance style to Bybit style (if needed)
        # Bybit: 1,3,5,15,30,60,120,240,360,720,D,M,W
        mapping = {"1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240", "1d": "D"}
        bybit_interval = mapping.get(interval, "60")
        
        resp = await self._request("GET", "/v5/market/kline", {
            "category": "linear",
            "symbol": symbol,
            "interval": bybit_interval,
            "limit": limit
        })
        
        if resp.get("retCode") == 0:
            klines = resp["result"]["list"]
            # Bybit klines: [start_time, open, high, low, close, volume, turnover]
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            return df.sort_values('timestamp')
        return pd.DataFrame()

    async def get_position(self, symbol: str) -> Dict:
        """Get position"""
        resp = await self._request("GET", "/v5/position/list", {"category": "linear", "symbol": symbol}, signed=True)
        if resp.get("retCode") == 0 and resp["result"]["list"]:
            pos = resp["result"]["list"][0]
            # Bybit size is string, can be signed
            size = float(pos["size"])
            side = pos["side"] # Buy or Sell
            amt = size if side == "Buy" else -size
            return {
                "symbol": symbol,
                "position_amt": amt,
                "entry_price": float(pos.get("avgPrice", 0)),
                "unrealized_pnl": float(pos.get("unrealisedPnl", 0)),
                "leverage": int(pos.get("leverage", 1))
            }
        return {"symbol": symbol, "position_amt": 0, "entry_price": 0, "unrealized_pnl": 0, "leverage": 1}

    async def get_all_positions(self) -> List[Dict]:
        """Get all positions"""
        resp = await self._request("GET", "/v5/position/list", {"category": "linear", "settleCoin": "USDT"}, signed=True)
        active = []
        if resp.get("retCode") == 0:
            for pos in resp["result"]["list"]:
                if float(pos["size"]) != 0:
                    size = float(pos["size"])
                    amt = size if pos["side"] == "Buy" else -size
                    active.append({
                        "symbol": pos["symbol"],
                        "position_amt": amt,
                        "entry_price": float(pos.get("avgPrice", 0)),
                        "unrealized_pnl": float(pos.get("unrealisedPnl", 0)),
                        "leverage": int(pos.get("leverage", 1)),
                        "mark_price": float(pos.get("markPrice", 0))
                    })
        return active

    async def place_market_order(self, symbol: str, side: str, quantity: float, reduce_only: bool = False) -> Dict:
        """Place market order"""
        # side: Buy or Sell
        side_formatted = "Buy" if side.upper() == "BUY" else "Sell"
        params = {
            "category": "linear",
            "symbol": symbol,
            "side": side_formatted,
            "orderType": "Market",
            "qty": str(quantity),
            "reduceOnly": reduce_only
        }
        return await self._request("POST", "/v5/order/create", params, signed=True)

    async def place_bracket_orders(self, symbol: str, position_side: str, quantity: float, stop_loss_price: Optional[float], take_profit_price: Optional[float]) -> Dict:
        """Place SL/TP orders (Bybit can set these during order creation or separately)"""
        # Implementing separate update for simplicity here
        params = {
            "category": "linear",
            "symbol": symbol,
            "takeProfit": str(take_profit_price) if take_profit_price else "",
            "stopLoss": str(stop_loss_price) if stop_loss_price else "",
            "tpOrderType": "Market",
            "slOrderType": "Market",
        }
        return await self._request("POST", "/v5/position/set-tpsl", params, signed=True)

    async def cancel_open_orders(self, symbol: str) -> int:
        """Cancel all orders for symbol"""
        resp = await self._request("POST", "/v5/order/cancel-all", {"category": "linear", "symbol": symbol}, signed=True)
        if resp.get("retCode") == 0:
            return 1 # Or more detailed count
        return 0

    async def change_leverage(self, symbol: str, leverage: int):
        """Change leverage"""
        await self._request("POST", "/v5/position/set-leverage", {
            "category": "linear",
            "symbol": symbol,
            "buyLeverage": str(leverage),
            "sellLeverage": str(leverage)
        }, signed=True)

    async def get_exchange_info(self) -> Dict:
        """Get symbols info"""
        return await self._request("GET", "/v5/market/instruments-info", {"category": "linear"})
