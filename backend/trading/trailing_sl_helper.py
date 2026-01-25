"""
Trailing Stop Loss Helper
Helper functions for trailing stop loss management
"""
from typing import Dict
from loguru import logger


async def move_sl_to_breakeven(binance_client, brackets, symbol: str, entry_price: float):
    """
    손절가를 본전으로 이동
    첫 부분 익절 후 호출
    """
    bracket = brackets.get(symbol)
    if not bracket:
        return
    
    side = bracket.get('side')
    current_sl = bracket.get('sl')
    
    if not side or not current_sl:
        return
    
    # 본전 가격 (약간의 여유 포함)
    if side == "LONG":
        breakeven_price = entry_price * 1.0002  # 0.02% 위
    else:
        breakeven_price = entry_price * 0.9998  # 0.02% 아래
    
    # 이미 본전보다 나은 SL이면 스킵
    if side == "LONG" and current_sl >= breakeven_price:
        return
    if side == "SHORT" and current_sl <= breakeven_price:
        return
    
    try:
        # 기존 SL 주문 취소
        if bracket.get('sl_order_id'):
            await binance_client.cancel_order(symbol, bracket['sl_order_id'])
        
        # 새 SL 주문 생성
        qty = bracket.get('qty', 0)
        stop_side = "SELL" if side == "LONG" else "BUY"
        
        new_sl_order = await binance_client.place_stop_market_order(
            symbol=symbol,
            side=stop_side,
            quantity=abs(qty),
            stop_price=breakeven_price,
            reduce_only=True
        )
        
        bracket['sl'] = breakeven_price
        bracket['sl_order_id'] = new_sl_order.get('orderId')
        
        logger.info(f"✅ {symbol} SL moved to breakeven @ {breakeven_price:.2f}")
        
    except Exception as e:
        logger.error(f"Failed to move SL to breakeven for {symbol}: {e}")


async def update_trailing_stop_loss(
    binance_client,
    brackets,
    symbol: str,
    current_price: float,
    entry_price: float,
    side: str,
    bracket: Dict
):
    """
    Trailing Stop Loss 업데이트
    수익 발생 시 손절가를 따라 올림/내림
    """
    current_sl = bracket.get('sl')
    leverage = bracket.get('leverage', 5)
    
    if not current_sl:
        return
    
    if side == "LONG":
        # 수익률 계산
        pnl_pct = (current_price - entry_price) / entry_price * 100 * leverage
        
        # +2% 이상 수익 → SL을 본전으로
        if pnl_pct >= 2.0 and current_sl < entry_price:
            new_sl = entry_price * 1.0001
            await update_stop_loss_order(binance_client, brackets, symbol, new_sl, side, bracket)
            logger.info(f"🛡️ {symbol} Trailing SL to breakeven @ {new_sl:.2f}")
        
        # +5% 이상 수익 → SL을 +2%로
        elif pnl_pct >= 5.0:
            target_sl = entry_price * 1.02
            if current_sl < target_sl:
                await update_stop_loss_order(binance_client, brackets, symbol, target_sl, side, bracket)
                logger.info(f"📈 {symbol} Trailing SL to +2% @ {target_sl:.2f}")
        
        # +10% 이상 수익 → SL을 +5%로
        elif pnl_pct >= 10.0:
            target_sl = entry_price * 1.05
            if current_sl < target_sl:
                await update_stop_loss_order(binance_client, brackets, symbol, target_sl, side, bracket)
                logger.info(f"🚀 {symbol} Trailing SL to +5% @ {target_sl:.2f}")
    
    elif side == "SHORT":
        # 수익률 계산
        pnl_pct = (entry_price - current_price) / entry_price * 100 * leverage
        
        # +2% 이상 수익 → SL을 본전으로
        if pnl_pct >= 2.0 and current_sl > entry_price:
            new_sl = entry_price * 0.9999
            await update_stop_loss_order(binance_client, brackets, symbol, new_sl, side, bracket)
            logger.info(f"🛡️ {symbol} Trailing SL to breakeven @ {new_sl:.2f}")
        
        # +5% 이상 수익 → SL을 -2%로
        elif pnl_pct >= 5.0:
            target_sl = entry_price * 0.98
            if current_sl > target_sl:
                await update_stop_loss_order(binance_client, brackets, symbol, target_sl, side, bracket)
                logger.info(f"📈 {symbol} Trailing SL to -2% @ {target_sl:.2f}")
        
        # +10% 이상 수익 → SL을 -5%로
        elif pnl_pct >= 10.0:
            target_sl = entry_price * 0.95
            if current_sl > target_sl:
                await update_stop_loss_order(binance_client, brackets, symbol, target_sl, side, bracket)
                logger.info(f"🚀 {symbol} Trailing SL to -5% @ {target_sl:.2f}")


async def update_stop_loss_order(
    binance_client,
    brackets,
    symbol: str,
    new_sl_price: float,
    side: str,
    bracket: Dict
):
    """SL 주문 업데이트 헬퍼"""
    try:
        # 기존 SL 취소
        if bracket.get('sl_order_id'):
            await binance_client.cancel_order(symbol, bracket['sl_order_id'])
        
        # 새 SL 생성
        qty = bracket.get('qty', 0)
        stop_side = "SELL" if side == "LONG" else "BUY"
        
        new_sl_order = await binance_client.place_stop_market_order(
            symbol=symbol,
            side=stop_side,
            quantity=abs(qty),
            stop_price=new_sl_price,
            reduce_only=True
        )
        
        bracket['sl'] = new_sl_price
        bracket['sl_order_id'] = new_sl_order.get('orderId')
        
    except Exception as e:
        logger.error(f"Failed to update SL for {symbol}: {e}")
