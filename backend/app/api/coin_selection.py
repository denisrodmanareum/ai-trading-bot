"""
Coin Selection API
Hybrid mode: Core coins + Auto-selected altcoins
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from loguru import logger

from app.services.coin_selector import coin_selector

router = APIRouter()


class CoinSelectionConfig(BaseModel):
    core_coins: Optional[List[str]] = None
    max_altcoins: Optional[int] = None
    max_total: Optional[int] = None
    rebalance_interval_hours: Optional[int] = None
    filters: Optional[Dict] = None
    scoring: Optional[Dict] = None


@router.get("/selection")
async def get_current_selection():
    """
    Get currently selected coins
    
    Returns:
        {
            'selected_coins': ['BTCUSDT', 'ETHUSDT', ...],
            'scores': {'BTCUSDT': 95.5, ...},
            'config': {...},
            'last_rebalance': '2026-01-22T...',
            'next_rebalance': '2026-01-22T...'
        }
    """
    try:
        coins = await coin_selector.get_selected_coins()
        
        return {
            "status": "success",
            "selected_coins": coins,
            "scores": coin_selector.coin_scores,
            "config": coin_selector.get_config(),
            "last_rebalance": coin_selector.last_rebalance.isoformat() if coin_selector.last_rebalance else None,
            "total_coins": len(coins)
        }
    except Exception as e:
        logger.error(f"Failed to get coin selection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rebalance")
async def trigger_rebalance():
    """
    Manually trigger rebalance
    
    Returns:
        {
            'selected_coins': [...],
            'scores': {...},
            'timestamp': '...'
        }
    """
    try:
        result = await coin_selector.rebalance()
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Failed to rebalance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_config():
    """Get current configuration"""
    try:
        config = coin_selector.get_config()
        return {"status": "success", "config": config}
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config")
async def update_config(config: CoinSelectionConfig):
    """
    Update configuration
    
    Body:
        {
            "core_coins": ["BTC", "ETH"],
            "max_altcoins": 5,
            "max_total": 7,
            "rebalance_interval_hours": 1,
            "filters": {...},
            "scoring": {...}
        }
    """
    try:
        # Convert to dict and remove None values
        config_dict = {k: v for k, v in config.dict().items() if v is not None}
        
        coin_selector.update_config(config_dict)
        
        # Trigger rebalance with new config
        result = await coin_selector.rebalance()
        
        return {
            "status": "success",
            "message": "Configuration updated and rebalanced",
            "result": result
        }
    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/candidates")
async def get_coin_candidates():
    """
    Get all coin candidates with scores
    (for UI display/selection)
    
    Returns:
        {
            'candidates': [
                {
                    'symbol': 'SOLUSDT',
                    'score': 85.5,
                    'metrics': {...}
                },
                ...
            ]
        }
    """
    try:
        # Force a fresh analysis
        import aiohttp
        
        futures_symbols = await coin_selector._get_binance_futures_symbols()
        market_data = await coin_selector._get_coingecko_market_data()
        scored_coins = await coin_selector._score_coins(futures_symbols, market_data)
        
        # Return top 30 candidates
        return {
            "status": "success",
            "candidates": scored_coins[:30],
            "total": len(scored_coins)
        }
    except Exception as e:
        logger.error(f"Failed to get candidates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_selection_stats():
    """
    Get statistics about current selection
    
    Returns:
        {
            'total_coins': 7,
            'core_coins': 2,
            'auto_coins': 5,
            'avg_score': 82.5,
            'score_range': [75.0, 95.0]
        }
    """
    try:
        coins = await coin_selector.get_selected_coins()
        scores = coin_selector.coin_scores
        core_coins = [f"{c}USDT" for c in coin_selector.config['core_coins']]
        
        auto_coins = [c for c in coins if c not in core_coins]
        
        score_values = list(scores.values())
        avg_score = sum(score_values) / len(score_values) if score_values else 0
        
        return {
            "status": "success",
            "stats": {
                "total_coins": len(coins),
                "core_coins": len(core_coins),
                "auto_coins": len(auto_coins),
                "avg_score": round(avg_score, 2),
                "score_range": [min(score_values), max(score_values)] if score_values else [0, 0],
                "coins_list": coins
            }
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
