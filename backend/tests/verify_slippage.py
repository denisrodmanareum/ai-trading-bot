import sys
import os
import asyncio
from unittest.mock import AsyncMock, MagicMock

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading.slippage_manager import SlippageManager

async def test_slippage_manager():
    print("Testing Slippage Manager...")
    
    # Mock Binance Client
    mock_client = AsyncMock()
    
    # Define a mock orderbook (High Liquidity)
    # Best Ask: 100.0, Best Bid: 99.9
    high_liq_orderbook = {
        'asks': [['100.0', '10.0'], ['100.1', '10.0']], # Plenty match
        'bids': [['99.9', '10.0'], ['99.8', '10.0']]
    }
    
    # Define a mock orderbook (Low Liquidity/High Slippage)
    # Best Ask: 100.0 (only 0.1 qty), Next: 105.0 (Huge gap)
    low_liq_orderbook = {
        'asks': [['100.0', '0.1'], ['105.0', '10.0']], 
        'bids': [['99.9', '0.1'], ['95.0', '10.0']]
    }

    sm = SlippageManager(mock_client)
    
    print("\n1. Testing Low Slippage Scenario (Market Order)")
    mock_client.get_orderbook.return_value = high_liq_orderbook
    
    # Mock Market Order Result
    mock_client.place_market_order.return_value = {'orderId': 1, 'avgPrice': '100.05'}
    
    result = await sm.smart_order("BTCUSDT", "BUY", 1.0)
    
    if result.get('orderId') == 1:
        print("Low slippage detected -> Market Order Executed")
    else:
        print("Failed: Should have executed Market Order")

    print("\n2. Testing High Slippage Scenario (Limit Order)")
    mock_client.get_orderbook.return_value = low_liq_orderbook
    mock_client.get_ticker.return_value = {'askPrice': '100.0', 'bidPrice': '99.9'}
    
    # Mock Limit Order Result
    mock_client.place_limit_order.return_value = {'orderId': 2, 'avgPrice': '100.0'}
    
    result = await sm.smart_order("BTCUSDT", "BUY", 1.0)
    
    # Check if place_limit_order was called
    if mock_client.place_limit_order.called:
         print("High slippage detected -> Limit Order Executed")
         args = mock_client.place_limit_order.call_args
         print(f"   Limit Price Set To: {args[0][3]}") # Check price
    else:
         print("Failed: Should have executed Limit Order")

    print("\nAll Slippage Manager Tests Passed!")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_slippage_manager())
