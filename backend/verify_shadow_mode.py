import asyncio
import logging
from unittest.mock import MagicMock, AsyncMock

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock dependencies
import sys
import os
sys.path.append(os.getcwd())

# Mock modules that might cause import errors if missing dependencies
sys.modules['trading.exchange_factory'] = MagicMock()
sys.modules['trading.base_client'] = MagicMock()
sys.modules['ai.agent'] = MagicMock()
sys.modules['app.services.price_stream'] = MagicMock()
sys.modules['app.services.websocket_manager'] = MagicMock()
sys.modules['app.core.config'] = MagicMock()

# Now import the service to test
from app.services.auto_trading import AutoTradingService

async def test_shadow_mode():
    logger.info("🧪 Starting Shadow Mode Verification...")
    
    # 1. Setup Service
    exchange_mock = AsyncMock()
    # Mock position return
    exchange_mock.get_position.return_value = {
        'symbol': 'BTCUSDT',
        'position_amt': 0.0,
        'entry_price': 0.0,
        'unrealized_pnl': 0.0,
        'leverage': 5
    }
    exchange_mock.get_account_info.return_value = {'balance': 1000, 'maint_margin': 0, 'margin_balance': 1000}
    # Mock klines for indicators
    import pandas as pd
    df = pd.DataFrame({
        'close': [100.0]*100,
        'high': [101.0]*100,
        'low': [99.0]*100,
        'volume': [1000.0]*100,
        'rsi': [50.0]*100, # Neutral
        'macd': [0.0]*100,
        'signal': [0.0]*100,
        'bb_upper': [110.0]*100,
        'bb_lower': [90.0]*100,
        'atr': [1.0]*100, 
        'ema_9': [100.0]*100,
        'ema_21': [100.0]*100,
        'ema_50': [100.0]*100,
        'stoch_k': [50.0]*100,
        'stoch_d': [50.0]*100,
    })
    # We need to mock get_klines to return this df, but AutoTradingService calls add_technical_indicators
    # so easier to mock `add_technical_indicators` in features
    
    exchange_mock.get_klines.return_value = df 
    
    service = AutoTradingService(exchange_mock, MagicMock())
    
    # Mock Agent
    service.agent = MagicMock()
    service.agent.live_predict.return_value = 0 # HOLD (Main Agent)
    service.agent.model = True # Pretend loaded
    
    # Mock Shadow Agent
    shadow_agent_mock = MagicMock()
    shadow_agent_mock.live_predict.return_value = 1 # LONG (Shadow Agent) -> Force a trade
    
    # Manually inject shadow agent to skip file loading
    service.shadow_agent = shadow_agent_mock
    service.shadow_running = True
    service.running = True # Main service must be running
    
    # 2. Simulate Market Data
    market_data = {
        'symbol': 'BTCUSDT',
        'close': 50000.0,
        'volume': 100.0,
        'is_closed': True
    }
    
    # Mock technical indicators injection
    # We will just patch the method in the instance or imports if needed.
    # But `_trade_logic` imports it. `from ai.features import add_technical_indicators`
    # Let's mock it in sys.modules first (too late?)
    # Easier: mock get_klines return value to be a DF that ALREADY has indicators?
    # No, the code calls `add_technical_indicators(df)`.
    # Let's mock `add_technical_indicators` function
    
    with MagicMock() as mock_features:
        sys.modules['ai.features'] = mock_features
        mock_features.add_technical_indicators = lambda x: x # Identity 
        
        # We need the dataframe returned by proper get_klines to have the columns
        # because the code accesses them: latest['rsi'], etc.
        # So we augment the DF in get_klines mock
        
        rich_df = df.copy() # Already has columns
        exchange_mock.get_klines.return_value = rich_df
        
        logger.info(f"Initial Shadow Portfolio: {service.shadow_portfolio}")
        
        # 3. Trigger Logic
        await service.process_market_data(market_data)
        
        # 4. Verify Results
        logger.info(f"Post-Trade Shadow Portfolio: {service.shadow_portfolio}")
        
        if service.shadow_portfolio['position_amt'] > 0:
            logger.info("✅ PASS: Shadow Agent successfully opened a LONG position (Virtual).")
        else:
            logger.error("❌ FAIL: Shadow Agent did not open position.")
            
        # 5. Simulate Price Move & Close
        shadow_agent_mock.live_predict.return_value = 3 # CLOSE
        market_data['close'] = 51000.0 # Price up
        
        await service.process_market_data(market_data)
        
        logger.info(f"Post-Close Shadow Portfolio: {service.shadow_portfolio}")
        
        if service.shadow_portfolio['position_amt'] == 0:
             logger.info("✅ PASS: Shadow Agent successfully closed position.")
             pnl = service.shadow_portfolio['balance'] - 10000.0
             logger.info(f"Virtual PnR: {pnl}")
             if pnl > 0:
                 logger.info("✅ PASS: Profit was realized.")
        else:
             logger.error("❌ FAIL: Shadow Agent did not close position.")

if __name__ == "__main__":
    asyncio.run(test_shadow_mode())
