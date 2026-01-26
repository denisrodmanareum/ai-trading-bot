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
        
        if main.exchange_client is None:
            raise HTTPException(status_code=503, detail="Exchange not connected")
        
        # 1. Basic Info
        account = await main.exchange_client.get_account_info()
        positions = await main.exchange_client.get_all_positions()
        
        # Prices
        btc_price = await main.exchange_client.get_current_price("BTCUSDT")
        eth_price = await main.exchange_client.get_current_price("ETHUSDT")
        sol_price = await main.exchange_client.get_current_price("SOLUSDT")
        
        total_unrealized_pnl = sum(pos['unrealized_pnl'] for pos in positions)
        funding_rate = await main.exchange_client.get_funding_rate("BTCUSDT")
        
        # 2. Market Metrics (Kimchi Premium - DISABLED for restricted network)
        kimp = 0.0
        btc_price_krw = 0.0
        usd_krw_rate = 1400.0 # Fallback
        btc_dominance = 0.0
        
        # NOTE: External API calls (Upbit, CoinGecko) removed to prevent DNS errors on restricted networks
        # If needed, implement a local calculation or use internal exchange data only.

        # 3. Additional Pro Metrics (Safely)
        mark_price_data = {}
        ticker_24h = {}
        try:
            mark_price_data = await main.exchange_client.get_mark_price_info(symbol="BTCUSDT")
            ticker_24h = await main.exchange_client.get_24h_ticker(symbol="BTCUSDT")
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
                "mark_price": mark_price_data.get('mark_price', 0),
                "index_price": mark_price_data.get('index_price', 0),
                "next_funding_time": mark_price_data.get('next_funding_time', 0),
                "high_24h": ticker_24h.get('high_24h', 0),
                "low_24h": ticker_24h.get('low_24h', 0),
                "volume_24h": ticker_24h.get('volume_24h', 0)
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
        
        if main.exchange_client is None:
            raise HTTPException(status_code=503, detail="Exchange not connected")
        
        klines = await main.exchange_client.get_raw_klines(
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent-trades")
async def get_dashboard_recent_trades(symbol: str = "BTCUSDT", limit: int = 30):
    """Fallback: Get recent trades via dashboard router"""
    try:
        import app.main as main
        if main.exchange_client is None:
            raise HTTPException(status_code=503, detail="Exchange not connected")
            
        return await main.exchange_client.get_recent_trades(symbol=symbol, limit=limit)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dashboard trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))