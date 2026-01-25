"""
Positions API Router
"""
from fastapi import APIRouter, HTTPException
from loguru import logger

router = APIRouter()


@router.get("")
async def get_positions():
    """Get all positions"""
    try:
        import app.main as main
        
        if main.exchange_client is None:
            raise HTTPException(status_code=503, detail="Exchange not connected")
        
        positions = await main.exchange_client.get_all_positions()
        return {"positions": positions}
        
    except Exception as e:
        logger.error(f"Failed to get positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))