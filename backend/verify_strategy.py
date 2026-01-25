import asyncio
import logging
from unittest.mock import MagicMock, AsyncMock
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock dependencies
import sys
import os
sys.path.append(os.getcwd())

sys.modules['trading.exchange_factory'] = MagicMock()
sys.modules['trading.base_client'] = MagicMock()
sys.modules['ai.agent'] = MagicMock()
sys.modules['app.services.price_stream'] = MagicMock()
sys.modules['app.services.scheduler'] = MagicMock()

from app.services.auto_trading import AutoTradingService
from trading.trading_strategy import StochasticTradingStrategy

async def test_strategy_logic():
    logger.info("🧪 Testing Strategy Logic: Rule Captain + AI Filter")

    # Setup Service
    exchange_mock = AsyncMock()
    exchange_mock.get_position.return_value = {
        'symbol': 'BTCUSDT', 'position_amt': 0.0, 'entry_price': 0.0, 
        'unrealized_pnl': 0.0, 'leverage': 5
    }
    
    agent_mock = MagicMock()
    # AutoTradingService(binance_client, shadow_agent=None)
    # It imports TradingAgent internally or globally.
    # We should patch the agent attribute after init if it creates one.
    
    # Mocking the internal TradingAgent creation if possible, or just overwrite it.
    service = AutoTradingService(exchange_mock, None)
    service.agent = agent_mock # Force inject mock
    service.running = True
    
    # helper to mock df
    def create_df(close_price, volume, rsi_val, stoch_k, stoch_d):
        return pd.DataFrame({
            'close': [close_price]*100,
            'high': [close_price*1.01]*100,
            'low': [close_price*0.99]*100,
            'volume': [volume]*100,
            'volume_sma': [volume]*100, 
            'atr': [1.0]*100,
            'ema_200': [close_price-10]*100,
            'stoch_k': [stoch_k]*100, 
            'stoch_d': [stoch_d]*100, 
            'rsi': [rsi_val]*100,
            'macd': [0.0]*100,
            'signal': [0.0]*100,
            'ema_9': [close_price]*100,
            'ema_21': [close_price]*100,
            'ema_50': [close_price]*100,
            'adx': [25.0]*100,
            'bb_upper': [110.0]*100,
            'bb_lower': [90.0]*100
        })

    # Mock add_technical_indicators to return df as is (since we create full df)
    sys.modules['ai.features'] = MagicMock()
    sys.modules['ai.features'].add_technical_indicators = lambda x: x

    # Create DF with indicators once
    df = create_df(100.0, 1000.0, 50.0, 20.0, 20.0) # RSI 50, Stoch 20
    exchange_mock.get_klines.return_value = df

    # Scenario 1: No Signal + AI Buy -> Should HOLD
    logger.info("\n--- Scenario 1: No Rule + AI Buy ---")
    service.stoch_strategy.should_enter = MagicMock(return_value=None)
    agent_mock.live_predict.return_value = 1 # LONG
    
    await service._trade_logic({'symbol': 'BTCUSDT', 'close': 100, 'high': 101, 'low': 99, 'volume': 1000, 'bb_upper': 110, 'bb_lower': 90, 'atr': 1})
    exchange_mock.place_market_order.assert_not_called()
    logger.info("✅ Result: No Order (AI alone blocked)")

    # Scenario 2: Strong Rule Buy + AI Sell -> Should BUY (Momentum overrides)
    logger.info("\n--- Scenario 2: Strong Rule Buy + AI Sell ---")
    
    # Needs mismatch to trigger leverage change
    exchange_mock.get_position.return_value['leverage'] = 1 
    
    # Mock place_market_order result
    exchange_mock.place_market_order.return_value = {'symbol': 'BTCUSDT', 'orderId': 123, 'price': '100.0', 'avgPrice': '100.0', 'executedQty': '0.001'}

    service.stoch_strategy.should_enter = MagicMock(return_value={
        "action": "LONG", "strength": 3, "leverage": 5, "reason": "Test Strong Buy"
    })
    agent_mock.live_predict.return_value = 2 # SHORT (Conflict)
    
    await service._trade_logic({'symbol': 'BTCUSDT', 'close': 100, 'high': 101, 'low': 99, 'volume': 1000, 'bb_upper': 110, 'bb_lower': 90, 'atr': 1})
    # We expect _execute_order to be called with action 1
    # Check if change_leverage called with 5
    exchange_mock.change_leverage.assert_called_with('BTCUSDT', 5)
    logger.info("✅ Result: Leverage set to 5x")

    # Scenario 3: Weak Rule Buy + AI Sell -> Should BLOCK
    logger.info("\n--- Scenario 3: Weak Rule Buy (Strength 1) + AI Sell ---")
    service.stoch_strategy.should_enter = MagicMock(return_value={
        "action": "LONG", "strength": 1, "leverage": 1, "reason": "Test Weak Buy"
    })
    agent_mock.live_predict.return_value = 2 # SHORT (Conflict)
    
    # Reset mocks
    exchange_mock.change_leverage.reset_mock()
    # Mock execute order to print
    service._execute_order = AsyncMock()
    
    await service._trade_logic({'symbol': 'BTCUSDT', 'close': 100, 'high': 101, 'low': 99, 'volume': 1000, 'bb_upper': 110, 'bb_lower': 90, 'atr': 1})
    
    service._execute_order.assert_called_with('BTCUSDT', 0,  exchange_mock.get_position.return_value, 100)
    logger.info("✅ Result: Action 0 (HOLD) - Execution Blocked")

    # Scenario 4: AI Close -> Should ALLOW (Exit)
    logger.info("\n--- Scenario 4: AI Close (Exit) ---")
    # Set position
    exchange_mock.get_position.return_value = {'symbol': 'BTCUSDT', 'position_amt': 0.1, 'entry_price': 90, 'unrealized_pnl': 10, 'leverage': 5}
    service.stoch_strategy.should_enter = MagicMock(return_value=None)
    agent_mock.live_predict.return_value = 3 # CLOSE
    
    await service._trade_logic({'symbol': 'BTCUSDT', 'close': 100, 'high': 101, 'low': 99, 'volume': 1000, 'bb_upper': 110, 'bb_lower': 90, 'atr': 1})
    service._execute_order.assert_called_with('BTCUSDT', 3, exchange_mock.get_position.return_value, 100)
    logger.info("✅ Result: Action 3 (CLOSE) - AI Exit Allowed")

if __name__ == "__main__":
    asyncio.run(test_strategy_logic())
