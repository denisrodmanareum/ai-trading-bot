"""
Trading API Router
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger
import asyncio

router = APIRouter()


@router.get("/symbols")
async def get_trading_symbols():
    """Get list of available trading symbols"""
    try:
        import app.main as main
        
        if main.exchange_client is None:
            # Return default symbols if exchange not initialized
            return {
                "symbols": [
                    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT",
                    "XRPUSDT", "DOGEUSDT", "DOTUSDT", "MATICUSDT", "AVAXUSDT",
                    "LINKUSDT", "ATOMUSDT", "NEARUSDT", "FTMUSDT", "APTUSDT",
                    "ARBUSDT", "OPUSDT", "SUIUSDT", "INJUSDT", "TIAUSDT"
                ]
            }
        
        # Get exchange info from Binance
        exchange_info = await main.exchange_client.get_exchange_info()
        
        # Filter USDT perpetual contracts
        symbols = [
            s['symbol'] 
            for s in exchange_info.get('symbols', [])
            if s['symbol'].endswith('USDT') 
            and s.get('status') == 'TRADING'
            and s.get('contractType') == 'PERPETUAL'
        ]
        
        # Sort alphabetically
        symbols.sort()
        
        return {
            "symbols": symbols[:100]  # Limit to top 100
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get symbols: {e}")
        # Fallback to default list
        return {
            "symbols": [
                "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT",
                "XRPUSDT", "DOGEUSDT", "DOTUSDT", "MATICUSDT", "AVAXUSDT",
                "LINKUSDT", "ATOMUSDT", "NEARUSDT", "FTMUSDT", "APTUSDT",
                "ARBUSDT", "OPUSDT", "SUIUSDT", "INJUSDT", "TIAUSDT"
            ]
        }
print("DEBUG: Trading Router Module Loaded") # Verify loading


class OrderRequest(BaseModel):
    symbol: str = "BTCUSDT"
    side: str
    quantity: float
    order_type: str = "MARKET" # MARKET or LIMIT
    price: float = None # Required for LIMIT


@router.post("/order")
async def place_order(order: OrderRequest):
    """Place market or limit order"""
    try:
        import app.main as main
        
        if main.exchange_client is None:
            raise HTTPException(status_code=503, detail="Exchange not connected")
        
        if order.order_type.upper() == "LIMIT":
            if not order.price or order.price <= 0:
                raise HTTPException(status_code=400, detail="Price required for limit order")
                
            result = await main.exchange_client.place_limit_order(
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=order.price
            )
        else:
            result = await main.exchange_client.place_market_order(
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity
            )
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to place order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/close-position")
async def close_position():
    """Close all positions"""
    try:
        import app.main as main
        
        if main.exchange_client is None:
            raise HTTPException(status_code=503, detail="Exchange not connected")
        
        positions = await main.exchange_client.get_all_positions()
        
        if not positions:
            return {"message": "No positions to close"}
        
        results = []
        for pos in positions:
            symbol = pos['symbol']
            position_amt = pos['position_amt']
            side = "SELL" if position_amt > 0 else "BUY"
            quantity = abs(position_amt)
            
            order = await main.exchange_client.place_market_order(
                symbol=symbol,
                side=side,
                quantity=quantity
            )
            results.append(order)
        
        return {
            "message": f"Closed {len(results)} position(s)",
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to close positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class LeverageRequest(BaseModel):
    symbol: str = "BTCUSDT"
    leverage: int


@router.post("/leverage")
async def change_leverage(request: LeverageRequest):
    """Change leverage"""
    try:
        import app.main as main
        
        if not 1 <= request.leverage <= 125:
             raise HTTPException(status_code=400, detail="Leverage must be between 1 and 125")
             
        resp = await main.exchange_client.change_leverage(
            symbol=request.symbol,
            leverage=request.leverage
        )
        return {"message": f"Leverage changed to {request.leverage}x", "data": resp}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change leverage failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/price/{symbol}")
async def get_price(symbol: str):
    """Get current price"""
    try:
        import app.main as main
        
        if main.exchange_client is None:
            raise HTTPException(status_code=503, detail="Exchange not connected")
        
        price = await main.exchange_client.get_current_price(symbol)
        return {"symbol": symbol, "price": price}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get price: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orderbook/{symbol}")
async def get_order_book(symbol: str):
    """Get order book"""
    try:
        import app.main as main
        
        if main.exchange_client is None:
            raise HTTPException(status_code=503, detail="Exchange not connected")
        
        depth = await main.exchange_client.get_order_book(symbol)
        return depth
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get order book: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/balance")
async def get_balance():
    """Get account balance"""
    try:
        import app.main as main
        
        if main.exchange_client is None:
            raise HTTPException(status_code=503, detail="Exchange not connected")
        
        account = await main.exchange_client.get_account_info()
        return account
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get balance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto/start")
async def start_auto_trading():
    """Start auto trading"""
    try:
        import app.main as main
        
        if main.auto_trading_service is None:
            raise HTTPException(status_code=503, detail="Auto trading service not initialized")
            
        await main.auto_trading_service.start()
        return {"status": "started", "message": "Auto trading started"}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start auto trading: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto/stop")
async def stop_auto_trading():
    """Stop auto trading"""
    try:
        import app.main as main
        
        if main.auto_trading_service is None:
            raise HTTPException(status_code=503, detail="Auto trading service not initialized")
            
        await main.auto_trading_service.stop()
        return {"status": "stopped", "message": "Auto trading stopped"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop auto trading: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auto/status")
async def get_auto_trading_status():
    """Get auto trading status"""
    try:
        import app.main as main
        
        if main.auto_trading_service is None:
            return {"running": False, "status": "not_initialized"}
            
        return {
            "running": main.auto_trading_service.running,
            "processing": main.auto_trading_service.processing
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Risk Management Endpoints

class RiskConfigRequest(BaseModel):
    daily_loss_limit: float = None
    max_margin_level: float = None
    kill_switch: bool = None
    position_mode: str = None # FIXED or RATIO
    position_ratio: float = None

@router.get("/risk/status")
async def get_risk_status():
    """Get current risk status"""
    import app.main as main
    if main.auto_trading_service is None:
        return {"status": "not_initialized"}
        
    service = main.auto_trading_service
    return {
        "daily_loss_limit": service.risk_config.daily_loss_limit,
        "max_margin_level": service.risk_config.max_margin_level,
        "kill_switch": service.risk_config.kill_switch,
        "position_mode": service.risk_config.position_mode,
        "position_ratio": service.risk_config.position_ratio,
        "current_daily_loss": service.current_daily_loss,
        "daily_start_balance": service.daily_start_balance,
        "risk_status": service.risk_status,
        "current_margin_level": service.last_margin_level
    }

@router.post("/risk/config")
async def update_risk_config(config: RiskConfigRequest):
    """Update risk configuration"""
    import app.main as main
    if main.auto_trading_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
        
    main.auto_trading_service.update_risk_config(
        daily_loss_limit=config.daily_loss_limit,
        max_margin_level=config.max_margin_level,
        kill_switch=config.kill_switch,
        position_mode=config.position_mode,
        position_ratio=config.position_ratio
    )
    return {"status": "updated", "config": config}


# Strategy Config Endpoints

class StrategyConfigRequest(BaseModel):
    mode: str = None  # SCALP or SWING
    selected_interval: str = None  # 15m, 30m, 1h, 4h, 1d
    leverage_mode: str = None  # AUTO or MANUAL
    manual_leverage: int = None

@router.get("/strategy/config")
async def get_strategy_config():
    """Get current strategy status"""
    import app.main as main
    if main.auto_trading_service is None:
        return {"status": "not_initialized"}
        
    s_config = main.auto_trading_service.strategy_config
    return {
        "mode": s_config.mode,
        "selected_interval": s_config.selected_interval,
        "available_intervals": s_config.get_available_intervals(),
        "leverage_mode": s_config.leverage_mode,
        "manual_leverage": s_config.manual_leverage
    }

@router.post("/strategy/config")
async def update_strategy_config(config: StrategyConfigRequest):
    """Update strategy configuration"""
    import app.main as main
    if main.auto_trading_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
        
    s_config = main.auto_trading_service.strategy_config
    
    # Use set_mode() to auto-set appropriate default interval when mode changes
    if config.mode:
        s_config.set_mode(config.mode)
    
    # Set selected interval (validate it's valid for current mode)
    if config.selected_interval:
        available = s_config.get_available_intervals()
        if config.selected_interval in available:
            s_config.selected_interval = config.selected_interval
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Interval {config.selected_interval} not valid for {s_config.mode} mode. Available: {available}"
            )
    
    if config.leverage_mode:
        s_config.leverage_mode = config.leverage_mode
        logger.info(f"⚙️ API: Leverage mode updated to {config.leverage_mode}")
    if config.manual_leverage:
        s_config.manual_leverage = int(config.manual_leverage)
        logger.info(f"⚙️ API: Manual leverage updated to {config.manual_leverage}x")
        
    return {"status": "updated", "config": {
        "mode": s_config.mode,
        "selected_interval": s_config.selected_interval,
        "available_intervals": s_config.get_available_intervals(),
        "leverage_mode": s_config.leverage_mode,
        "manual_leverage": s_config.manual_leverage
    }}

# --- COIN SELECTION ENDPOINTS ---

@router.get("/coins/selected")
async def get_selected_coins():
    """Get currently selected trading coins"""
    from app.services.coin_selector import coin_selector
    
    try:
        status = coin_selector.get_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get selected coins: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class CoinSelectionRequest(BaseModel):
    coins: list[str]  # ['BTCUSDT', 'ETHUSDT', ...]

@router.post("/coins/select")
async def select_trading_coins(request: CoinSelectionRequest):
    """Set selected trading coins"""
    from app.services.coin_selector import coin_selector
    
    try:
        coin_selector.set_selected_coins(request.coins)
        return {
            "success": True,
            "selected_coins": coin_selector.selected_coins,
            "count": len(coin_selector.selected_coins)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to set selected coins: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- MANUAL TRADE MANAGEMENT ENDPOINTS ---

@router.post("/sync")
async def sync_data():
    """Force sync data from Exchange (clears ghost records)"""
    try:
        import app.main as main
        if main.exchange_client is None:
             raise HTTPException(status_code=503, detail="Exchange not connected")
             
        # Fetch real trades from Exchange (includes Realized PnL & Commission)
        user_trades = await main.exchange_client.get_user_trades("BTCUSDT", limit=50)
        
        from app.database import SessionLocal
        from app.models import Trade
        from datetime import datetime, timezone
        
        count = 0
        async with SessionLocal() as session:
            # Optional: Clear old trades to avoid duplicates if ID matching is hard, 
            # OR better: Upsert based on timestamp/price/qty match?
            # User wants a clean history. Let's truncate and refill for simplicity if user requests 'Reset'
            # But here we just want to ADD missing info or populate.
            # To avoid duplicates without unique TradeID in DB, we'll just check if similar trade exists.
            
            # Actually, standard approach:
            for t in user_trades:
                # Binance Trade: {'id': 123, 'orderId': 456, 'price': '90000', 'qty': '0.001', 'commission': '0.04', 'realizedPnl': '-0.5', 'side': 'SELL', 'time': 170...}
                
                # Check if exists (dedupe by timestamp approx)
                ts = datetime.fromtimestamp(t['time'] / 1000.0)
                
                # Simple dedupe: Check if a trade with same timestamp exists
                # In production, we should add 'trade_id' column to model.
                # For now, let's assume we proceed.
                
                # We will just INSERT for now. If user clicks sync multiple times, might duplicate.
                # Let's delete all first? No, that deletes 'Reason'.
                # Let's just update the latest trades or insert.
                
            # Compromise: Delete all trades from DB and refill from Exchange for accuracy of PnL.
            # But we lose "Reason". 
            # User cares more about PnL.
            pass

        # STRATEGY: Wipe and Refill Last 50 Trades to ensure PnL is correct.
        # Warning: Loses 'Strategy' and 'Reason' metadata if not careful.
        # But since current data is ghost/broken, refill is better.
        
        # await session.execute("DELETE FROM trades") # too dangerous?
        # Let's just add them and let user clear history if they want.
        # Wait, user sees "0.00". 
        
        # Better: Just update PnL on existing trades?
        # Timestamps won't match exactly between internal Log and Exchange execution time.
        
        # BEST: Just Insert new 'Realized' trades from Exchange.
        # And user can "Clear History" to remove the ghost ones.
            pass

            # IMPLEMENTATION:
            # We will fetch trades. If they look new (time > last_db_trade), insert.
            # But the user wants PnL on *existing* rows.
            # Since existing rows are just "Orders", we can't easily attach PnL unless we matched OrderID.
            # We don't have OrderID.
            
            # DECISION: We will DELETE logic here and instead return the fetched trades to Frontend?
            # No, Frontend reads from DB via /api/history.
            # So we MUST save to DB.
            
            # Let's wipe table and refill. It's the cleanest for "Sync".
            # (Reason/Strategy will be set to 'Imported')
            
            # Clear table
            from sqlalchemy import text
            await session.execute(text("DELETE FROM trades"))
            
            for t in user_trades:
                pnl = t['pnl']
                commission = t['commission']
                price = t['price']
                qty = t['qty']
                side = t['side'] # BUY / SELL
                action = "LONG" if side == "BUY" else "SHORT" # Simplified
                
                trade = Trade(
                    symbol=t['symbol'],
                    action=side,
                    side=side,
                    price=price,
                    quantity=qty,
                    pnl=pnl,
                    commission=commission,
                    strategy="exchange_sync",
                    reason="Imported from Exchange",
                    timestamp=datetime.fromtimestamp(t['time'] / 1000.0, timezone.utc)
                )
                session.add(trade)
                count += 1
            
            await session.commit()

        return {"status": "synced", "message": f"Synced {count} trades from Exchange (History Replaced)"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/orders")
async def get_open_orders(symbol: str = "BTCUSDT"):
    """Get open orders for symbol"""
    try:
        import app.main as main
        if main.exchange_client is None:
             raise HTTPException(status_code=503, detail="Exchange not connected")
             
        orders = await main.exchange_client.get_open_orders(symbol)
        return orders
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/positions")
async def get_active_positions():
    """Get all active positions"""
    try:
        import app.main as main
        if main.exchange_client is None:
             raise HTTPException(status_code=503, detail="Exchange not connected")
             
        positions = await main.exchange_client.get_all_positions()
        return positions
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/order/{symbol}/{order_id}")
async def cancel_order(symbol: str, order_id: int):
    """Cancel specific order"""
    try:
        import app.main as main
        if main.exchange_client is None:
             raise HTTPException(status_code=503, detail="Exchange not connected")
             
        result = await main.exchange_client.cancel_order(symbol, order_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel order: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cancel-all")
async def cancel_all_orders(symbol: str = "BTCUSDT"):
    """Cancel all orders for symbol"""
    try:
        import app.main as main
        if main.exchange_client is None:
             raise HTTPException(status_code=503, detail="Exchange not connected")
        
        # Exchange API usually has cancelAll, but we can loop if client doesn't support it directly yet.
        # Our simplified client doesn't have cancel_all, so we fetch and loop.
        orders = await main.exchange_client.get_open_orders(symbol)
        results = []
        for o in orders:
            res = await main.exchange_client.cancel_order(symbol, o['orderId'])
            results.append(res)
            
        return {"message": f"Cancelled {len(results)} orders", "details": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel all: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/close-position/{symbol}")
async def close_specific_position(symbol: str):
    """Close position for specific symbol"""
    try:
        import app.main as main
        if main.exchange_client is None:
             raise HTTPException(status_code=503, detail="Exchange not connected")
             
        position = await main.exchange_client.get_position(symbol)
        amt = position['position_amt']
        
        if amt == 0:
            return {"message": f"No open position for {symbol}"}
            
        side = "SELL" if amt > 0 else "BUY"
        quantity = abs(amt)
        
        order = await main.exchange_client.place_market_order(symbol, side, quantity, reduce_only=True)
        return {"message": f"Closed {symbol} position", "order": order}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to close position {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades/recent")
async def get_recent_trades(symbol: str = "BTCUSDT", limit: int = 30):
    """Get recent market trades for display in Last Trades panel"""
    try:
        import app.main as main
        
        if main.exchange_client is None:
            raise HTTPException(status_code=503, detail="Exchange not connected")
        
        return await main.exchange_client.get_recent_trades(symbol=symbol, limit=limit)
        
        # Format for frontend
        formatted_trades = [{
            "id": t['id'],
            "price": t['price'],
            "qty": t['qty'],
            "time": t['time'],
            "is_buyer_maker": t['isBuyerMaker']  # True = sell order filled (red), False = buy order filled (green)
        } for t in trades]
        
        return formatted_trades
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recent trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))




@router.get("/ticker/{symbol}")
async def get_ticker_info(symbol: str):
    """Get comprehensive ticker info for header"""
    try:
        import app.main as main
        if main.exchange_client is None:
            raise HTTPException(status_code=503, detail="Exchange not connected")
        
        # Parallel fetch for speed
        mark_info, ticker_info = await asyncio.gather(
            main.exchange_client.get_mark_price_info(symbol=symbol),
            main.exchange_client.get_24h_ticker(symbol=symbol)
        )
        
        return {
            "symbol": symbol,
            "mark_price": mark_info.get('mark_price', 0),
            "index_price": mark_info.get('index_price', 0),
            "funding_rate": 0.0, # Not provided by unified mark_price_info yet
            "next_funding_time": mark_info.get('next_funding_time', 0),
            "high_24h": ticker_info.get('high_24h', 0),
            "low_24h": ticker_info.get('low_24h', 0),
            "volume_24h": ticker_info.get('volume_24h', 0),
            "turnover_24h": 0.0,
            "price_change_pct": 0.0
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get ticker info for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))