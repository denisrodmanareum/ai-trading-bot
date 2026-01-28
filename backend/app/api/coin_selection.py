"""
Coin Selection API (Shim for Manual Selection System)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from loguru import logger
from datetime import datetime

from app.services.coin_selector import coin_selector

router = APIRouter()


class CoinSelectionConfig(BaseModel):
    mode: Optional[str] = None
    core_coins: Optional[List[str]] = None
    max_altcoins: Optional[int] = None
    max_total: Optional[int] = None


@router.get("/selection")
async def get_current_selection():
    """
    Get currently selected coins (Shim)
    """
    try:
        status = coin_selector.get_status()
        
        # Return common format expected by legacy UI if any
        return {
            "status": "success",
            "selected_coins": status['selected_coins'],
            "scores": {}, # No longer used
            "config": coin_selector.get_config(),
            "last_rebalance": status['last_update'],
            "total_coins": status['count']
        }
    except Exception as e:
        logger.error(f"Failed to get coin selection shim: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rebalance")
async def trigger_rebalance():
    """
    Manual rebalance (noop in manual mode)
    """
    return {"status": "success", "message": "Manual mode active, rebalance skipped"}


@router.get("/config")
async def get_config():
    """Get current configuration"""
    try:
        config = coin_selector.get_config()
        return {"status": "success", "config": config}
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/candidates")
async def get_coin_candidates():
    """
    Get all coin candidates (Simple list)
    """
    # Just return a hardcoded list or empty for now since we use manual selection
    return {
        "status": "success",
        "candidates": [],
        "total": 0
    }


@router.get("/stats")
async def get_selection_stats():
    """
    Get statistics about current selection
    """
    try:
        status = coin_selector.get_status()
        return {
            "status": "success",
            "stats": {
                "total_coins": status['count'],
                "core_coins": 2,
                "auto_coins": 0,
                "avg_score": 0,
                "score_range": [0, 0],
                "coins_list": status['selected_coins']
            }
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
