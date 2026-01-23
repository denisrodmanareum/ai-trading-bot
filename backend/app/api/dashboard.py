"""
Dashboard API Router
"""
from fastapi import APIRouter, HTTPException
from typing import Dict
from loguru import logger

router = APIRouter()


@router.get("/overview")
async def get_dashboard_overview() -> Dict:
    """Get dashboard overview data"""
    try:
        import app.main as main
        
        if main.binance_client is None:
            raise HTTPException(status_code=503, detail="Binance not connected")
        
        # 1. Basic Info
        account = await main.binance_client.get_account_info()
        positions = await main.binance_client.get_all_positions()
        
        # Prices
        btc_price = await main.binance_client.get_current_price("BTCUSDT")
        eth_price = await main.binance_client.get_current_price("ETHUSDT")
        sol_price = await main.binance_client.get_current_price("SOLUSDT")
        
        total_unrealized_pnl = sum(pos['unrealized_pnl'] for pos in positions)
        funding_rate = await main.binance_client.get_funding_rate("BTCUSDT")
        
        # 2. Market Metrics (Kimchi Premium)
        kimp = 0.0
        btc_price_krw = 0.0
        usd_krw_rate = 1400.0 # Fallback
        btc_dominance = 0.0
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                # Upbit Price
                async with session.get('https://api.upbit.com/v1/ticker?markets=KRW-BTC') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        btc_price_krw = float(data[0]['trade_price'])
                
                # Exchange Rate
                async with session.get('https://open.er-api.com/v6/latest/USD') as resp:
                     if resp.status == 200:
                         data = await resp.json()
                         usd_krw_rate = float(data['rates']['KRW'])
                         
                async with session.get('https://api.coingecko.com/api/v3/global') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        btc_dominance = float(data['data']['market_cap_percentage']['btc'])
                        
            if btc_price > 0 and usd_krw_rate > 0:
                converted_krw_to_usd = btc_price_krw / usd_krw_rate
                kimp = ((converted_krw_to_usd / btc_price) - 1) * 100
                
        except Exception as e:
            logger.warning(f"Failed to fetch market metrics: {e}")

        # 3. Additional Pro Metrics (Safely)
        mark_price_data = {}
        ticker_24h = {}
        try:
            mark_price_data = await main.binance_client.client.futures_mark_price(symbol="BTCUSDT")
            ticker_24h = await main.binance_client.client.futures_ticker(symbol="BTCUSDT")
        except Exception as e:
            logger.error(f"Failed to get mark/ticker data: {e}")

        return {
            "account": account,
            "positions": positions,
            "prices": {
                "BTCUSDT": btc_price,
                "ETHUSDT": eth_price,
                "SOLUSDT": sol_price
            },
            "btc_price": btc_price,
            "total_unrealized_pnl": total_unrealized_pnl,
            "market_metrics": {
                "funding_rate": funding_rate,
                "kimchi_premium": kimp,
                "btc_dominance": btc_dominance, 
                "usd_krw": usd_krw_rate,
                "btc_krw": btc_price_krw,
                "mark_price": float(mark_price_data.get('markPrice', 0)),
                "index_price": float(mark_price_data.get('indexPrice', 0)),
                "next_funding_time": int(mark_price_data.get('nextFundingTime', 0)),
                "high_24h": float(ticker_24h.get('highPrice', 0)),
                "low_24h": float(ticker_24h.get('lowPrice', 0)),
                "volume_24h": float(ticker_24h.get('volume', 0))
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get dashboard overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chart-data/{symbol}")
async def get_chart_data(symbol: str, interval: str = "1m", limit: int = 50):
    """Get chart data"""
    try:
        import app.main as main
        
        if main.binance_client is None:
            raise HTTPException(status_code=503, detail="Binance not connected")
        
        klines = await main.binance_client.get_raw_klines(
            symbol=symbol,
            interval=interval,
            limit=limit
        )
        
        data = []
        for k in klines:
            data.append({
                'timestamp': int(k[0]),
                'open': float(k[1]),
                'high': float(k[2]),
                'low': float(k[3]),
                'close': float(k[4]),
                'volume': float(k[5])
            })
        
        return {"symbol": symbol, "interval": interval, "data": data}
        
    except Exception as e:
        logger.error(f"Failed to get chart data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports")
async def get_reports(limit: int = 10):
    """Get historical daily reports"""
    try:
        from app.database import SessionLocal
        from app.models import DailyReport
        from sqlalchemy import select
        
        async with SessionLocal() as session:
            query = select(DailyReport).order_by(DailyReport.date.desc()).limit(limit)
            result = await session.execute(query)
            reports = result.scalars().all()
            return reports
    except Exception as e:
        logger.error(f"Failed to get reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reports/generate")
async def trigger_report():
    """Manually trigger a report for today (Debug/Manual)"""
    try:
        import app.main as main
        if main.reporter_service is None:
             raise HTTPException(status_code=503, detail="Reporter service not running")
        
        remark = await main.reporter_service.generate_daily_report()
        
        if remark is None:
            return {"status": "no_trades", "message": "No trades found for today"}
            
        return {"status": "success", "remark": remark}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent-trades")
async def get_dashboard_recent_trades(symbol: str = "BTCUSDT", limit: int = 30):
    """Fallback: Get recent trades via dashboard router"""
    try:
        import app.main as main
        if main.binance_client is None:
            raise HTTPException(status_code=503, detail="Binance not connected")
            
        trades = await main.binance_client.client.futures_recent_trades(symbol=symbol, limit=limit)
        return [{
            "id": t['id'],
            "price": t['price'],
            "qty": t['qty'],
            "time": t['time'],
            "is_buyer_maker": t['isBuyerMaker']
        } for t in trades]
    except Exception as e:
        logger.error(f"Failed to get dashboard trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))