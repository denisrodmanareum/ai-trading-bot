"""
History API Router
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from loguru import logger
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/trades")
async def get_trades(
    limit: int = 50,
    offset: int = 0,
    symbol: Optional[str] = None
):
    """Get trade history from DB"""
    try:
        from app.database import SessionLocal
        from app.models import Trade
        from sqlalchemy import select, desc
        
        async with SessionLocal() as session:
            query = select(Trade)
            if symbol:
                query = query.where(Trade.symbol == symbol)
            
            query = query.order_by(desc(Trade.timestamp)).offset(offset).limit(limit)
            result = await session.execute(query)
            trades = result.scalars().all()
            
            # Explicitly serialize to dict
            trades_list = [
                {
                    "id": trade.id,
                    "symbol": trade.symbol,  # 명시적으로 symbol 포함
                    "action": trade.action,
                    "side": trade.side,
                    "price": trade.price,
                    "quantity": trade.quantity,
                    "pnl": trade.pnl,
                    "commission": trade.commission,
                    "strategy": trade.strategy,
                    "reason": trade.reason,
                    "timestamp": trade.timestamp.isoformat() if trade.timestamp else None
                }
                for trade in trades
            ]
            
            logger.debug(f"Returning {len(trades_list)} trades")
            if trades_list:
                logger.debug(f"First trade symbol: {trades_list[0]['symbol']}")
            
            return {"trades": trades_list}
        
    except Exception as e:
        logger.error(f"Failed to get trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """Get trading statistics from DB"""
    try:
        from app.database import SessionLocal
        from app.models import Trade
        from sqlalchemy import select, func
        
        async with SessionLocal() as session:
            # 1. Total Trades
            query_total = select(func.count(Trade.id))
            result_total = await session.execute(query_total)
            total_trades = result_total.scalar_one()
            
            if total_trades == 0:
                return {
                    "total_trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "win_rate": 0.0,
                    "total_pnl": 0.0
                }

            # 2. Wins (PnL > 0)
            query_wins = select(func.count(Trade.id)).where(Trade.pnl > 0)
            result_wins = await session.execute(query_wins)
            wins = result_wins.scalar_one()
            
            # 3. Total PnL & Commissions
            query_pnl = select(func.sum(Trade.pnl))
            result_pnl = await session.execute(query_pnl)
            total_pnl = result_pnl.scalar_one() or 0.0
            
            query_comm = select(func.sum(Trade.commission))
            result_comm = await session.execute(query_comm)
            total_commission = result_comm.scalar_one() or 0.0
            
            losses = total_trades - wins
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
            
            return {
                "total_trades": total_trades,
                "wins": wins,
                "losses": losses,
                "win_rate": round(win_rate, 2),
                "total_pnl": round(total_pnl, 2),
                "total_commission": round(total_commission, 2),
                "net_pnl": round(total_pnl - total_commission, 2)
            }
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily/{date}")
async def get_daily_stats(date: str):
    """Get statistics for specific date"""
    try:
        # 실제 구현 시 해당 날짜 데이터 조회
        stats = {
            "date": date,
            "trades": 12,
            "wins": 8,
            "losses": 4,
            "pnl": 125.50,
            "win_rate": 66.7
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get daily stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/record")
async def record_trade(trade_data: dict):
    """Record a new trade"""
    try:
        # 실제 구현 시 데이터베이스에 저장
        logger.info(f"Recording trade: {trade_data}")
        
        return {"status": "recorded", "trade_id": 1}
        
    except Exception as e:
        logger.error(f"Failed to record trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
async def export_trades(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    format: str = "csv"
):
    """Export trade history"""
    try:
        # CSV 또는 Excel 형식으로 내보내기
        # 실제 구현 시 pandas로 파일 생성
        
        return {
            "message": "Export ready",
            "download_url": "/downloads/trades_export.csv"
        }
        
    except Exception as e:
        logger.error(f"Failed to export: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/clear")
async def clear_history():
    """Clear all trade history"""
    try:
        from app.database import SessionLocal
        from app.models import Trade
        from sqlalchemy import delete
        
        async with SessionLocal() as session:
            await session.execute(delete(Trade))
            await session.commit()
            
            return {"status": "success", "message": "History cleared"}
            
    except Exception as e:
        logger.error(f"Failed to clear history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/report/generate")
async def generate_report(force: bool = True):
    """Manually trigger daily report generation"""
    try:
        import app.main as main
        if main.reporter_service:
            # Generate for today (UTC)
            date = datetime.utcnow().date()
            remark = await main.reporter_service.generate_daily_report(date)
            return {"status": "success", "remark": remark, "date": date}
        else:
            raise HTTPException(status_code=503, detail="Reporter service not available")
            
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports")
async def get_reports(limit: int = 10):
    """Get list of daily reports"""
    try:
        from app.database import SessionLocal
        from app.models import DailyReport
        from sqlalchemy import select, desc
        
        async with SessionLocal() as session:
            query = select(DailyReport).order_by(desc(DailyReport.date)).limit(limit)
            result = await session.execute(query)
            reports = result.scalars().all()
            return reports
            
    except Exception as e:
        logger.error(f"Failed to get reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))
