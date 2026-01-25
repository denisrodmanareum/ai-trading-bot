"""
AI Analysis Endpoints
- Analyze manual positions
- Daily review and recommendations
- Performance tracking
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List
from loguru import logger
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.database import get_db
from trading.exchange_factory import ExchangeFactory
from ai.daily_review import DailyReviewAnalyzer
from ai.stop_loss_ai import StopLossTakeProfitAI
from ai.agent import TradingAgent
from ai.market_regime import MarketRegimeDetector
from app.core.config import settings

router = APIRouter()

# Global instances
daily_reviewer = DailyReviewAnalyzer()
sltp_ai = StopLossTakeProfitAI()
regime_detector = MarketRegimeDetector()


@router.get("/ai/analyze-positions")
async def analyze_positions(db: Session = Depends(get_db)):
    """
    Analyze all current positions with AI
    Returns recommendations for each position
    """
    try:
        exchange_client = await ExchangeFactory.get_client()
        
        # Get current positions
        positions = await exchange_client.get_all_positions()
        active_positions = [p for p in positions if abs(p['position_amt']) > 0]
        
        if not active_positions:
            return {
                'status': 'no_positions',
                'message': 'No active positions to analyze',
                'analysis': []
            }
        
        analysis_results = []
        
        for position in active_positions:
            symbol = position['symbol']
            
            try:
                # Fetch market data
                df = await exchange_client.get_klines(symbol, '15m', limit=100)
                
                # df is already a processed DataFrame from get_klines in our clients
                df['close'] = df['close'].astype(float)
                df['high'] = df['high'].astype(float)
                df['low'] = df['low'].astype(float)
                df['volume'] = df['volume'].astype(float)
                
                # Add indicators
                from ai.features import add_technical_indicators
                df = add_technical_indicators(df)
                
                latest = df.iloc[-1]
                
                # Detect market regime
                regime_info = regime_detector.detect_regime(df)
                
                # Get SL/TP recommendations
                sltp_recommendation = sltp_ai.get_sl_tp_for_position(
                    position=position,
                    current_market_data=latest.to_dict()
                )
                
                # Calculate position health
                entry_price = position['entry_price']
                current_price = latest['close']
                position_amt = position['position_amt']
                unrealized_pnl = position['unrealized_pnl']
                
                # Direction check
                is_long = position_amt > 0
                price_change_pct = ((current_price - entry_price) / entry_price) * 100
                
                # AI Recommendation
                recommendation = "HOLD"
                confidence = 0.5
                reasoning = []
                
                # Rule 1: Check if position is against trend
                if regime_info['regime'] == 'TRENDING':
                    if is_long and latest.get('macd', 0) < latest.get('signal', 0):
                        recommendation = "CLOSE"
                        confidence = 0.7
                        reasoning.append("Trend reversal detected - MACD bearish crossover")
                    elif not is_long and latest.get('macd', 0) > latest.get('signal', 0):
                        recommendation = "CLOSE"
                        confidence = 0.7
                        reasoning.append("Trend reversal detected - MACD bullish crossover")
                
                # Rule 2: Check RSI extremes
                rsi = latest.get('rsi', 50)
                if is_long and rsi > 70:
                    recommendation = "CLOSE" if confidence < 0.7 else recommendation
                    confidence = max(confidence, 0.6)
                    reasoning.append(f"RSI overbought ({rsi:.1f}) - consider taking profit")
                elif not is_long and rsi < 30:
                    recommendation = "CLOSE" if confidence < 0.7 else recommendation
                    confidence = max(confidence, 0.6)
                    reasoning.append(f"RSI oversold ({rsi:.1f}) - consider closing SHORT")
                
                # Rule 3: Check unrealized PnL
                pnl_pct = (unrealized_pnl / (entry_price * abs(position_amt))) * 100
                
                if pnl_pct > 5:  # Profit > 5%
                    recommendation = "TAKE_PROFIT"
                    confidence = 0.8
                    reasoning.append(f"Strong profit ({pnl_pct:.2f}%) - consider securing gains")
                elif pnl_pct < -3:  # Loss > 3%
                    recommendation = "CLOSE"
                    confidence = 0.9
                    reasoning.append(f"Loss exceeding threshold ({pnl_pct:.2f}%) - cut losses")
                
                # Rule 4: High volatility warning
                if regime_info['regime'] == 'HIGH_VOLATILITY':
                    reasoning.append("High volatility detected - monitor closely")
                
                analysis_results.append({
                    'symbol': symbol,
                    'side': 'LONG' if is_long else 'SHORT',
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'unrealized_pnl': unrealized_pnl,
                    'pnl_pct': round(pnl_pct, 2),
                    'price_change_pct': round(price_change_pct, 2),
                    'recommendation': recommendation,
                    'confidence': round(confidence, 2),
                    'reasoning': reasoning,
                    'market_regime': regime_info['regime'],
                    'rsi': round(rsi, 1),
                    'sl_price': sltp_recommendation['sl_price'],
                    'tp_price': sltp_recommendation['tp_price'],
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Failed to analyze {symbol}: {e}")
                analysis_results.append({
                    'symbol': symbol,
                    'error': str(e),
                    'recommendation': 'HOLD',
                    'confidence': 0.5
                })
        
        return {
            'status': 'success',
            'total_positions': len(active_positions),
            'analysis': analysis_results,
            'generated_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Position analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai/daily-review")
async def get_daily_review(date: str = None, db: Session = Depends(get_db)):
    """
    Get AI's daily performance review
    """
    try:
        # Parse date
        if date:
            review_date = datetime.strptime(date, '%Y-%m-%d')
        else:
            review_date = datetime.now() - timedelta(days=1)
        
        # Fetch trades from DB
        from app.models import Trade
        start_of_day = review_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        trades = db.query(Trade).filter(
            Trade.timestamp >= start_of_day,
            Trade.timestamp < end_of_day
        ).all()
        
        # Convert to dict
        trades_data = [
            {
                'symbol': t.symbol,
                'side': t.side,
                'pnl': t.pnl or 0,
                'quantity': t.quantity,
                'entry_price': t.entry_price,
                'exit_price': t.exit_price,
                'timestamp': t.timestamp.isoformat(),
                'entry_time': t.entry_time.isoformat() if t.entry_time else None,
                'exit_time': t.exit_time.isoformat() if t.exit_time else None
            }
            for t in trades
        ]
        
        # Perform daily review
        review = daily_reviewer.analyze_daily_performance(trades_data, review_date)
        
        return review
        
    except Exception as e:
        logger.error(f"Daily review failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai/weekly-summary")
async def get_weekly_summary():
    """
    Get weekly performance summary
    """
    try:
        summary = daily_reviewer.get_weekly_summary()
        return summary
    except Exception as e:
        logger.error(f"Weekly summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai/improvement-suggestions")
async def get_improvement_suggestions():
    """
    Get AI improvement suggestions based on recent performance
    """
    try:
        suggestions = daily_reviewer.suggest_ai_improvements()
        return suggestions
    except Exception as e:
        logger.error(f"Improvement suggestions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/trigger-daily-review")
async def trigger_daily_review(db: Session = Depends(get_db)):
    """
    Manually trigger daily review (normally runs automatically)
    """
    try:
        yesterday = datetime.now() - timedelta(days=1)
        
        # Fetch yesterday's trades
        from app.models import Trade
        start_of_day = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        trades = db.query(Trade).filter(
            Trade.timestamp >= start_of_day,
            Trade.timestamp < end_of_day
        ).all()
        
        trades_data = [
            {
                'symbol': t.symbol,
                'side': t.side,
                'pnl': t.pnl or 0,
                'quantity': t.quantity,
                'entry_price': t.entry_price,
                'exit_price': t.exit_price,
                'timestamp': t.timestamp.isoformat(),
                'entry_time': t.entry_time.isoformat() if t.entry_time else None,
                'exit_time': t.exit_time.isoformat() if t.exit_time else None
            }
            for t in trades
        ]
        
        # Run review
        review = daily_reviewer.analyze_daily_performance(trades_data, yesterday)
        
        logger.info(f"Daily review completed for {yesterday.strftime('%Y-%m-%d')}")
        
        return {
            'status': 'success',
            'message': 'Daily review completed',
            'review': review
        }
        
    except Exception as e:
        logger.error(f"Trigger daily review failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
