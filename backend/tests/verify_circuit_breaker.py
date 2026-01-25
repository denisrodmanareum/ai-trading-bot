import sys
import os
import time
import logging

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.auto_trading import CircuitBreaker

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CircuitBreakerTest")

def test_circuit_breaker():
    logger.info("Testing Circuit Breaker...")
    cb = CircuitBreaker()
    
    # 1. Test Normal State
    logger.info("1. Checking Initial State (Expect NORMAL)")
    if cb.check_status():
        logger.error("Failed: Initial state should be NORMAL")
        return
    logger.info("Initial state OK")
    
    # 2. Test Minor Trigger (Tier 1: 1% loss in 15m)
    logger.info("2. Testing Tier 1 Trigger (Injecting -1.1% loss)")
    cb.record_trade(-1.1) # Direct 1.1% loss
    
    is_paused = cb.check_status()
    if is_paused and cb.triggered_tier == 'MINOR':
        logger.info(f"Tier 1 Triggered successfully: {cb.triggered_tier}")
    else:
        logger.error(f"Failed: Expected MINOR trigger, got {cb.triggered_tier}")
        return

    # 3. Simulate Time Passing (Fast Forward)
    logger.info("3. Simulating Wait (Resetting state manually for test)")
    cb.paused_until = None # Force reset
    cb.recent_losses = [] # Clear history
    
    # 4. Test Severe Trigger (Tier 3: 3% loss in 60m)
    logger.info("4. Testing Tier 3 Trigger (Injecting multiple losses)")
    cb.record_trade(-1.5)
    cb.record_trade(-1.6) # Total -3.1%
    
    is_paused = cb.check_status()
    if is_paused and cb.triggered_tier == 'SEVERE':
        logger.info(f"Tier 3 Triggered successfully: {cb.triggered_tier}")
        logger.info(f"   Paused until: {time.ctime(cb.paused_until)}")
    else:
        logger.error(f"Failed: Expected SEVERE trigger, got {cb.triggered_tier}")
        return
        
    logger.info("All Circuit Breaker Tests Passed!")

if __name__ == "__main__":
    test_circuit_breaker()
