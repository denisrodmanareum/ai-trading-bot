"""
Webhook API
Receive external trading signals from TradingView, etc.
"""
from fastapi import APIRouter, Request, HTTPException
from loguru import logger
from typing import Dict


router = APIRouter()


@router.post("/tradingview")
async def tradingview_webhook(request: Request):
    """
    TradingView 웹훅 수신
    
    Expected payload:
    {
        "ticker": "BTCUSDT",
        "action": "buy" | "sell" | "close",
        "price": 65000.0,
        "indicator": "Strategy name",
        "passphrase": "secret"
    }
    """
    try:
        data = await request.json()
        logger.info(f"📬 Webhook received: {data}")
        
        # 인증 (Optional)
        passphrase = data.get('passphrase')
        if passphrase != "your_secret_passphrase":
            raise HTTPException(status_code=401, detail="Invalid passphrase")
        
        # 시그널 파싱
        signal = {
            'symbol': data.get('ticker', 'BTCUSDT'),
            'action': data.get('action', 'close').upper(),
            'price': float(data.get('price', 0)),
            'indicator': data.get('indicator', 'Unknown'),
            'source': 'TradingView'
        }
        
        # 자동매매 시스템에 전달
        # (실제로는 auto_trading_service 인스턴스에 접근 필요)
        logger.info(f"✅ Signal processed: {signal}")
        
        return {
            "status": "received",
            "signal": signal
        }
        
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/generic")
async def generic_webhook(request: Request):
    """
    범용 웹훅
    
    Expected payload:
    {
        "symbol": "BTCUSDT",
        "side": "LONG" | "SHORT" | "CLOSE",
        "strength": 1-5,
        "reason": "Description"
    }
    """
    try:
        data = await request.json()
        logger.info(f"📬 Generic webhook: {data}")
        
        signal = {
            'symbol': data.get('symbol'),
            'side': data.get('side'),
            'strength': int(data.get('strength', 3)),
            'reason': data.get('reason', 'External signal'),
            'source': 'Generic'
        }
        
        return {
            "status": "received",
            "signal": signal
        }
        
    except Exception as e:
        logger.error(f"Generic webhook failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/test")
async def test_webhook():
    """웹훅 테스트 엔드포인트"""
    return {
        "status": "ok",
        "message": "Webhook endpoint is working"
    }
