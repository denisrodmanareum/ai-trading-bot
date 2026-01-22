"""
Auto Trading Service
"""
import asyncio
from typing import Optional, Dict
from loguru import logger
from datetime import datetime, timedelta
import time

from trading.binance_client import BinanceClient
from ai.agent import TradingAgent
from app.services.price_stream import PriceStreamService
from app.services.websocket_manager import WebSocketManager
from app.core.config import settings
from trading.trading_strategy import StochasticTradingStrategy
from ai.spike_detector import SpikeDetector
from ai.market_regime import MarketRegimeDetector
from ai.position_sizer import PositionSizer
from ai.stop_loss_ai import StopLossTakeProfitAI
from ai.multi_timeframe import MultiTimeframeAnalyzer
from app.services.coin_selector import coin_selector
import os
import pandas as pd

class RiskConfig:
    """Risk Management Configuration"""
    def __init__(self, daily_loss_limit=50.0, max_margin_level=0.8, kill_switch=False, position_mode="FIXED", position_ratio=0.1):
        self.daily_loss_limit = daily_loss_limit # USDT
        self.max_margin_level = max_margin_level # Maintenance Margin / Margin Balance
        self.kill_switch = kill_switch # If True, no new trades allowed
        self.position_mode = position_mode # "FIXED" or "RATIO"
        self.position_ratio = position_ratio # 0.1 = 10% of balance

class StrategyConfig:
    """Strategy Configuration (Manual Overrides)"""
    
    # Interval to seconds mapping for prediction timing
    INTERVAL_SECONDS = {
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400
    }
    
    # Available intervals per mode
    SCALP_INTERVALS = ["15m", "30m"]
    SWING_INTERVALS = ["1h", "4h", "1d"]
    
    def __init__(self, mode="SCALP", leverage_mode="AUTO", manual_leverage=5, autonomy_mode="AGGRESSIVE", selected_interval="15m"):
        self.mode = mode  # "SCALP" or "SWING"
        self.leverage_mode = leverage_mode  # "AUTO" or "MANUAL"
        self.manual_leverage = manual_leverage
        self.autonomy_mode = autonomy_mode  # "CONSERVATIVE" or "AGGRESSIVE"
        self.selected_interval = selected_interval  # Active trading interval
    
    def get_available_intervals(self):
        """Get available intervals for current mode"""
        if self.mode == "SWING":
            return self.SWING_INTERVALS
        return self.SCALP_INTERVALS
    
    def set_mode(self, mode: str):
        """Set trading mode and auto-select appropriate default interval"""
        self.mode = mode
        if mode == "SWING" and self.selected_interval not in self.SWING_INTERVALS:
            self.selected_interval = "1h"  # Default for SWING
        elif mode == "SCALP" and self.selected_interval not in self.SCALP_INTERVALS:
            self.selected_interval = "15m"  # Default for SCALP
    
    def get_prediction_interval_seconds(self):
        """Get prediction interval in seconds based on selected timeframe"""
        return self.INTERVAL_SECONDS.get(self.selected_interval, 900)


class CircuitBreaker:
    """
    Safety Mechanism to trigger panic stop
    Triggers if: Loss exceeds X% within Y minutes
    Action: Pause trading for Z minutes
    """
    def __init__(self, loss_threshold_pct=2.0, window_minutes=60, pause_minutes=30):
        self.loss_threshold_pct = loss_threshold_pct # e.g., 2% loss
        self.window_minutes = window_minutes
        self.pause_minutes = pause_minutes
        self.recent_losses = [] # List of (timestamp, loss_pct)
        self.paused_until: Optional[float] = None # Timestamp

    def record_trade(self, pnl_pct: float):
        """Record trade result"""
        if pnl_pct < 0:
            self.recent_losses.append((time.time(), abs(pnl_pct)))
            self._cleanup()
        
    def _cleanup(self):
        """Remove old records"""
        cutoff = time.time() - (self.window_minutes * 60)
        self.recent_losses = [x for x in self.recent_losses if x[0] > cutoff]
        
    def check_status(self) -> bool:
        """
        Check if circuit breaker is active.
        Returns: True if PAUSED (Safe mode), False if NORMAL
        """
        now = time.time()
        
        # 1. Check if already paused
        if self.paused_until and now < self.paused_until:
            return True
        elif self.paused_until:
             self.paused_until = None # Reset
             logger.info("✅ Circuit Breaker Lifted - Resuming Trading")

        # 2. Check recent losses
        self._cleanup()
        total_loss_pct = sum(x[1] for x in self.recent_losses)
        
        if total_loss_pct >= self.loss_threshold_pct:
            self.paused_until = now + (self.pause_minutes * 60)
            logger.critical(f"CIRCUIT BREAKER TRIGGERED! Total Loss {total_loss_pct:.2f}% in last {self.window_minutes}m. Pausing for {self.pause_minutes}m.")
            return True
            
        return False

class AutoTradingService:
    """
    Automated Trading Service
    Connects real-time price stream -> AI Agent -> Order Execution
    """
    
    def __init__(self, binance_client: BinanceClient, ws_manager: WebSocketManager = None):
        self.binance_client = binance_client
        self.ws_manager = ws_manager
        self.agent: Optional[TradingAgent] = None
        self.running = False
        self.processing = False
        self.last_prediction_time = 0
        self.prediction_interval = 60 # Seconds (1 minute candles)
        
        # Risk Management
        self.risk_config = RiskConfig()
        self.strategy_config = StrategyConfig() # New Config
        self.allowed_symbols = ["BTCUSDT"] # Safety: Only trade supported/trained symbols
        self.daily_start_balance = 0.0
        self.current_daily_loss = 0.0
        self.last_margin_level = 0.0
        self.risk_status = "NORMAL" # NORMAL, WARNING, STOPPED
        
        # Stochastic Strategy
        self.stoch_strategy = StochasticTradingStrategy()
        
        # Spike Detector
        self.spike_detector = SpikeDetector()
        
        # AI Components (NEW!)
        self.regime_detector = MarketRegimeDetector()
        self.position_sizer = PositionSizer()
        self.sl_tp_ai = StopLossTakeProfitAI()
        self.mtf_analyzer = MultiTimeframeAnalyzer(binance_client)
        
        # Shadow Mode (A/B Testing)
        self.shadow_agent: Optional[TradingAgent] = None
        self.shadow_running = False
        self.shadow_portfolio = {
            "balance": 10000.0, # Virtual Balance
            "position_amt": 0.0,
            "entry_price": 0.0,
            "unrealized_pnl": 0.0,
            "total_trades": 0,
            "win_trades": 0
        }
        
        # Circuit Breaker
        self.circuit_breaker = CircuitBreaker()
        
    async def initialize(self):
        """Initialize AI agent"""
        try:
            self.agent = TradingAgent()
            
            # Load latest model
            model_dir = settings.AI_MODEL_PATH
            if os.path.exists(model_dir):
                models = [f for f in os.listdir(model_dir) if f.endswith('.zip')]
                if models:
                    latest_model = os.path.join(model_dir, sorted(models)[-1])
                    self.agent.load_model(latest_model)
                    logger.info(f"AutoTrading: Loaded model {latest_model}")
                else:
                    logger.warning("AutoTrading: No trained models found, creating new one...")
                    await self._create_new_model()
            else:
                logger.warning("AutoTrading: Models directory not found, creating new one...")
                os.makedirs(model_dir, exist_ok=True)
                await self._create_new_model()
        except Exception as e:
            logger.error(f"AutoTrading init failed: {e}")
            
    async def _create_new_model(self):
        """Create and save a new initial model"""
        try:
            logger.info("Creating new initial AI model...")
            
            # 1. Fetch historical data for environment
            df = await self.binance_client.get_klines("BTCUSDT", interval="1h", limit=1000)
            from ai.features import add_technical_indicators
            df = add_technical_indicators(df)
            
            # 2. Build model
            # Dummy env for initialization
            env = self.agent.create_environment(df)
            from stable_baselines3.common.vec_env import DummyVecEnv
            vec_env = DummyVecEnv([lambda: env])
            
            self.agent.build_model(vec_env)
            
            # 3. Save model
            save_path = os.path.join(settings.AI_MODEL_PATH, "initial_model.zip")
            self.agent.save_model(save_path)
            logger.info(f"✅ Created and saved new model: {save_path}")
            
        except Exception as e:
            logger.error(f"Failed to create new model: {e}")
            raise

    async def start(self):
        """Start auto trading"""
        if self.running:
            return
            
        if not self.agent or not self.agent.model:
            await self.initialize()
            if not self.agent or not self.agent.model:
                raise ValueError("Cannot start auto trading: No AI model loaded")
        
        # Initialize Daily Balance for Risk Calc
        try:
            account = await self.binance_client.get_account_info()
            self.daily_start_balance = account['balance']
            self.current_daily_loss = 0.0
            self.risk_status = "NORMAL"
            logger.info(f"Risk Monitor Initialized. Start Balance: ${self.daily_start_balance:.2f}")
        except Exception as e:
            logger.error(f"Failed to init risk monitor: {e}")
            
        self.running = True
        logger.info("Auto Trading Started")

    async def check_risk_limits(self, account_info: Dict):
        """Check if trading should be stopped due to risk limits"""
        if self.risk_config.kill_switch:
             return False, "Kill Switch Active"

        # 1. Daily Loss Check
        current_balance = account_info['balance']
        pnl = current_balance - self.daily_start_balance
        self.current_daily_loss = -pnl if pnl < 0 else 0.0
        
        if self.current_daily_loss >= self.risk_config.daily_loss_limit:
            self.risk_status = "STOPPED"
            await self.stop()
            msg = f"Daily Loss Limit Hit! Loss: ${self.current_daily_loss:.2f} > Limit: ${self.risk_config.daily_loss_limit:.2f}"
            logger.critical(msg)
            return False, msg
            
        # 2. Margin Level Check
        # Maintenance Margin / Margin Balance
        maint_margin = account_info.get('maint_margin', 0)
        margin_balance = account_info.get('margin_balance', 1) # Avoid div by zero
        
        if margin_balance > 0:
            margin_level = maint_margin / margin_balance
            self.last_margin_level = margin_level
            
            if margin_level >= self.risk_config.max_margin_level:
                 self.risk_status = "WARNING"
                 msg = f"High Margin Level! {margin_level*100:.1f}% (Limit: {self.risk_config.max_margin_level*100:.1f}%)"
                 logger.warning(msg)
                 return False, msg

        return True, "OK"
        
    def update_risk_config(self, daily_loss_limit=None, max_margin_level=None, kill_switch=None, position_mode=None, position_ratio=None):
        """Update risk configuration"""
        if daily_loss_limit is not None:
            self.risk_config.daily_loss_limit = daily_loss_limit
        if max_margin_level is not None:
            self.risk_config.max_margin_level = max_margin_level
        if kill_switch is not None:
            self.risk_config.kill_switch = kill_switch
            if kill_switch:
                logger.warning("🛑 Kill Switch Activated Manually")
            else:
                logger.info("✅ Kill Switch Deactivated")
        if position_mode is not None:
            self.risk_config.position_mode = position_mode
        if position_ratio is not None:
            self.risk_config.position_ratio = position_ratio

    async def stop(self):
        """Stop auto trading"""
        self.running = False
        await self.stop_shadow_mode() # Stop shadow too
        logger.info("Auto Trading Stopped")

    async def start_shadow_mode(self, model_path: str = None, model_paths: list[str] = None):
        """Start Shadow Mode (A/B Testing)"""
        try:
            from ai.agent import TradingAgent
            from ai.ensemble import EnsembleAgent
            
            if model_paths and len(model_paths) > 1:
                self.shadow_agent = EnsembleAgent(model_paths)
                logger.info(f"Shadow Mode Started with Ensemble: {model_paths}")
            else:
                path = model_path or (model_paths[0] if model_paths else None)
                if not path:
                     raise ValueError("No model path provided for shadow mode")
                
                self.shadow_agent = TradingAgent()
                self.shadow_agent.load_model(path)
                logger.info(f"👻 Shadow Mode Started with Model: {path}")

            self.shadow_running = True
            # Reset virtual portfolio
            self.shadow_portfolio = {
                "balance": 10000.0,
                "position_amt": 0.0,
                "entry_price": 0.0,
                "unrealized_pnl": 0.0,
                "total_trades": 0,
                "win_trades": 0
            }
            
        except Exception as e:
            logger.error(f"Failed to start Shadow Mode: {e}")
            raise

    async def stop_shadow_mode(self):
        """Stop Shadow Mode"""
        self.shadow_running = False
        self.shadow_agent = None
        logger.info("Shadow Mode Stopped")

    def get_shadow_status(self):
        """Get current shadow mode status"""
        return {
            "running": self.shadow_running,
            "portfolio": self.shadow_portfolio
        }

    async def process_market_data(self, data: Dict):
        """Process incoming market data (called by PriceStream callback)"""
        if not self.running or self.processing:
            return

        # Check whether symbol is allowed for auto trading
        if data.get('symbol') not in self.allowed_symbols:
            # logger.debug(f"Skipping auto-trade for {data.get('symbol')}: Not in allowed list")
            return

        # Check interval (avoid duplicate processing for same candle)
        # Assuming data comes every minute or tick
        if data.get('is_closed'): # Only trade on closed candles for stability
            self.processing = True
            try:
                # RISK CHECK BEFORE TRADING
                account = await self.binance_client.get_account_info()
                if account is None:
                    logger.warning("Could not fetch account info for risk check, skipping.")
                    return

                safe, reason = await self.check_risk_limits(account)
                
                if not safe:
                    logger.warning(f"Risk Check Failed: {reason}")
                    return
                
                # CIRCUIT BREAKER CHECK
                if self.circuit_breaker.check_status():
                    # Just verify if we still need to log
                    # logger.warning("Trading Paused due to Circuit Breaker") 
                    return

                await self._trade_logic(data)
            except Exception as e:
                logger.error(f"AutoTrading error: {e}")
            finally:
                self.processing = False

    async def _trade_logic(self, data: Dict):
        """Core trading logic"""
        symbol = data['symbol']
        
        # 0. Check if coin is in selected list (Hybrid mode)
        selected_coins = await coin_selector.get_selected_coins()
        if symbol not in selected_coins:
            # Skip if not in selected coins
            return
        
        # 1. Get current position
        position = await self.binance_client.get_position(symbol)
        if position is None:
            logger.warning(f"Could not fetch position for {symbol}, skipping trade logic.")
            return
        # Need to construct the state dictionary expected by agent
        market_state = {
            'close': data['close'],
            'volume': data['volume'],
            # Note: In a real scenario, we need to calculate indicators here 
            # or rely on the stream to provide them. 
            # For this implementation, we might need to fetch recent klines to calc indicators
            # similar to trainer.py logic, or improve PriceStream to send indicators.
            # For now, we will fetch recent history to be safe and accurate.
        }
        
        # Fetch detailed analytics for accurate prediction
        # (This adds latency but ensures indicators are correct)
        # Fetch detailed analytics for accurate prediction
        # (This adds latency but ensures indicators are correct)
        # 1. Fetch data based on selected interval (For Strategy & AI)
        trading_interval = self.strategy_config.selected_interval
        logger.info(f"Trading Mode: {self.strategy_config.mode} | Interval: {trading_interval}")
        df = await self.binance_client.get_klines(symbol, interval=trading_interval, limit=100)
        from ai.features import add_technical_indicators
        df = add_technical_indicators(df)
        
        # 2. Fetch 1M Data (For Spike Detection)
        # We need recent 1m candles to detect sudden moves
        df_1m_raw = await self.binance_client.get_klines(symbol, interval='1m', limit=30)
        df_1m = pd.DataFrame(df_1m_raw, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df_1m[col] = df_1m[col].astype(float)
            
        # --- SPIKE DETECTION ---
        spike_result = self.spike_detector.analyze(df_1m, df.iloc[-1]['atr'])
        if spike_result['detected']:
            logger.warning(f"Spike Detected! {spike_result['reason_str']} (Score: {spike_result['score']:.2f})")
        # -----------------------
        
        # Calculate Stochastic Triple
        from trading.stochastic_triple import StochasticTriple
        stoch_calc = StochasticTriple(df['high'], df['low'], df['close'])
        stochs = stoch_calc.calculate()
        
        latest = df.iloc[-1]
        
        # Update market state with comprehensive indicators
        market_state.update({
            'rsi': float(latest['rsi']),
            'macd': float(latest['macd']),
            'signal': float(latest['signal']),
            'bb_upper': float(latest['bb_upper']),
            'bb_lower': float(latest['bb_lower']),
            'atr': float(latest['atr']),
            
            # Stochastic Triple
            'stoch_k_fast': float(stochs['fast']['k'].iloc[-1]),
            'stoch_d_fast': float(stochs['fast']['d'].iloc[-1]),
            'stoch_k_mid': float(stochs['mid']['k'].iloc[-1]),
            'stoch_d_mid': float(stochs['mid']['d'].iloc[-1]),
            'stoch_k_slow': float(stochs['slow']['k'].iloc[-1]),
            'stoch_d_slow': float(stochs['slow']['d'].iloc[-1]),
            
            'position': 1 if position['position_amt'] > 0 else (-1 if position['position_amt'] < 0 else 0),
            'position_size': abs(float(position['position_amt'])),
            'entry_price': float(position['entry_price']),
            'unrealized_pnl': float(position['unrealized_pnl'])
        })
        
        # 3. Market Regime Detection (NEW!)
        regime_info = self.regime_detector.detect_regime(df)
        current_regime = regime_info['regime']
        regime_confidence = regime_info['confidence']
        regime_params = regime_info['strategy_params']
        
        logger.info(f"Market Regime: {current_regime} (Confidence: {regime_confidence:.2f})")
        
        # 4. AI Prediction (AI acts as FILTER/VALIDATOR)
        ai_action = self.agent.live_predict(market_state)
        ai_action_name = ["HOLD", "LONG", "SHORT", "CLOSE"][ai_action]
        
        # 5. Tech Signal (Rules are the CAPTAIN)
        tech_signal = self.stoch_strategy.should_enter(df)
        
        # --- STRATEGY MODE FILTER + MARKET REGIME (ENHANCED) ---
        # Apply regime-based filtering
        if tech_signal:
            signal_strength = tech_signal.get('strength', 1)
            
            # Regime-based signal filtering
            if not self.regime_detector.should_trade(current_regime, signal_strength):
                logger.warning(f"Signal blocked by regime: {current_regime} requires strength >= {regime_params['min_signal_strength']}")
                tech_signal = None
        
        # Original strategy mode filter (enhanced with regime)
        if self.strategy_config.mode == "SWING" and tech_signal:
             # Filter out weak/fast signals in Swing Mode
             min_strength = max(2, regime_params['min_signal_strength'])
             if tech_signal['strength'] < min_strength and "Momentum" not in tech_signal['reason']:
                 tech_signal = None 
                 
             # SWING SAFETY: If Spike Detected OR High Volatility Regime, BLOCK trade
             if spike_result['detected'] or current_regime == "HIGH_VOLATILITY":
                 logger.warning(f"SWING Mode Safety: Blocked trade (Spike: {spike_result['detected']}, Regime: {current_regime})")
                 tech_signal = None
                 
        elif self.strategy_config.mode == "SCALP":
             # SCALP: More permissive but still respect HIGH_VOLATILITY regime
             if current_regime == "HIGH_VOLATILITY" and not spike_result['detected']:
                 # Allow scalping in high vol only with spike confirmation
                 logger.info("SCALP Mode: High Volatility - requires spike confirmation")
             elif spike_result['detected']:
                 logger.info("SCALP Mode: Trading in High Volatility Zone")
        # -----------------------------

        final_action = 0 # Default HOLD
        leverage = 5
        reason = "Wait"

        if tech_signal:
             # Rule-based Signal Exists
             rule_action_id = 1 if tech_signal['action'] == "LONG" else 2
             
             # AI FILTER LOGIC
             ai_opposes = (rule_action_id == 1 and ai_action == 2) or (rule_action_id == 2 and ai_action == 1)
             
             if ai_opposes and tech_signal['strength'] < 3:
                 logger.warning(f"AI Blocked Rule: Rule {tech_signal['action']} vs AI {ai_action_name}")
                 final_action = 0 # Blocked
                 reason = "AI_BLOCKED"
             else:
                 final_action = rule_action_id
                 
                 # --- LEVERAGE LOGIC (Enhanced with Regime) ---
                 if self.strategy_config.leverage_mode == "MANUAL":
                     leverage = self.strategy_config.manual_leverage
                 else:
                     base_leverage = tech_signal.get('leverage', 5)
                     # Adjust leverage based on market regime
                     leverage = self.regime_detector.adjust_leverage(base_leverage, current_regime)
                     logger.info(f"Leverage adjusted by regime: {base_leverage} -> {leverage}")
                 # ----------------------
                 
                 reason = f"Rule_{tech_signal.get('reason', 'Signal')}"
                 
                 # Apply Dynamic Leverage (only if no position and different from current)
                 try:
                     current_leverage = position.get('leverage', 5)
                     position_size = abs(float(position.get('positionAmt', 0)))
                     
                     # Only try to change leverage if:
                     # 1. Current leverage is different from desired leverage
                     # 2. No open position (Binance doesn't allow leverage change with open position)
                     if current_leverage != leverage and position_size == 0:
                         result = await self.binance_client.change_leverage(symbol, leverage)
                         if result is not None:
                             logger.info(f"✓ Leverage changed: {current_leverage} -> {leverage}")
                         else:
                             logger.debug(f"Leverage change failed, using current: {current_leverage}")
                             leverage = current_leverage
                     elif current_leverage != leverage and position_size > 0:
                         # Position exists, can't change leverage - use current
                         logger.debug(f"Position exists ({position_size}), using current leverage {current_leverage}")
                         leverage = current_leverage  # Use existing leverage
                 except Exception as e:
                     # Fallback to current leverage on any error
                     logger.debug(f"Leverage change error ({e}), using current: {current_leverage}")
                     leverage = current_leverage

        else:
            # No Rule Signal
            # --- AI-FIRST ENTRY LOGIC (Enhanced with Regime) ---
            # If no technical signal, but AI has strong conviction AND regime allows, allow entry.
            ai_first_allowed = regime_params.get('allow_ai_first', False)
            
            if ai_action in [1, 2] and ai_first_allowed:
                 final_action = ai_action
                 # Use regime-adjusted leverage for AI-first trades
                 base_leverage = 5
                 leverage = self.regime_detector.adjust_leverage(base_leverage, current_regime)
                 reason = f"AI_First_{current_regime}"
                 logger.info(f"AI-Initiated Trade: {ai_action_name} | Regime: {current_regime} | Lev: {leverage}x")
            elif ai_action in [1, 2] and not ai_first_allowed:
                 logger.info(f"AI wants to trade but regime {current_regime} blocks AI-first entries")
                 final_action = 0
                 reason = "AI_Blocked_By_Regime"
                 
            elif position['position_amt'] != 0 and ai_action == 3:
                final_action = 3 # Allow AI to close
                reason = "AI_CLOSE"
            else:
                final_action = 0 # No rule = No trade
                reason = "No_Signal"
        
        final_action_str = ["HOLD", "LONG", "SHORT", "CLOSE"][final_action]
        logger.info(f"AI: {ai_action_name} | Rule: {tech_signal['action'] if tech_signal else 'None'} -> Final: {final_action_str} ({reason})")
        
        # 5. Execute Order (Main)
        await self._execute_order(symbol, final_action, position, latest['close'], atr=market_state.get('atr', 0))

        # 5. Shadow Mode Logic
        if self.shadow_running and self.shadow_agent:
            try:
                # Shadow agent sees the same state
                # Note: Technically shadow agent should see its OWN position state, not real position state.
                # But for simplicity, we pass market data. 
                # Ideally we constructing a shadow_market_state with virtual position info.
                
                shadow_state = market_state.copy()
                shadow_state.update({
                    'position': 1 if self.shadow_portfolio['position_amt'] > 0 else (-1 if self.shadow_portfolio['position_amt'] < 0 else 0),
                    'position_size': abs(self.shadow_portfolio['position_amt']),
                    'entry_price': self.shadow_portfolio['entry_price'],
                    'unrealized_pnl': self.shadow_portfolio['unrealized_pnl']
                })
                
                shadow_action = self.shadow_agent.live_predict(shadow_state)
                await self._execute_shadow_trade(symbol, shadow_action, latest['close']) # Use latest close price
                
            except Exception as e:
                logger.error(f"Shadow Logic Error: {e}")

    async def _execute_order(self, symbol: str, action: int, position: Dict, price: float, atr: float = 0.0):
        """Execute order based on action"""
        current_amt = position['position_amt']
        
        # Quantity logic
        # 1. Calculate Target Notional Value
        if self.risk_config.position_mode == "RATIO":
            # Use a percentage of the start balance (or current balance)
            # Fetching current account for most accurate balance
            try:
                account = await self.binance_client.get_account_info()
                current_balance = account['balance']
                target_notional = current_balance * self.risk_config.position_ratio
            except:
                target_notional = 150.0 # Fallback
        else:
            # FIXED mode
            target_notional = 150.0

        # 2. Ensure min notional > 100 USDT (Binance Testnet Limit)
        # Using 120 as a safe floor even in RATIO mode
        safe_notional = max(target_notional, 120.0) 
        
        min_qty = safe_notional / price
        quantity = max(0.002, min_qty) # Ensure at least 0.002 BTC
        quantity = round(quantity, 3) # Specific for BTC (3 decimal places)

        if symbol != "BTCUSDT":
            quantity = 1 # Logic for other coins needed
            
        try:
            if action == 1: # LONG
                if current_amt <= 0: # If short or flat
                    if current_amt < 0: # Close short first
                        await self.binance_client.place_market_order(symbol, "BUY", abs(current_amt), reduce_only=True)
                    # Open long
                    order = await self.binance_client.place_market_order(symbol, "BUY", quantity)
                    logger.info("Executed LONG")
                    await self._broadcast_trade("LONG", symbol, quantity, order)
                    
            elif action == 2: # SHORT
                if current_amt >= 0: # If long or flat
                    if current_amt > 0: # Close long first
                         await self.binance_client.place_market_order(symbol, "SELL", abs(current_amt), reduce_only=True)
                    # Open short
                    order = await self.binance_client.place_market_order(symbol, "SELL", quantity)
                    logger.info("Executed SHORT")
                    await self._broadcast_trade("SHORT", symbol, quantity, order)
                    
            elif action == 3: # CLOSE
                if current_amt != 0:
                    side = "SELL" if current_amt > 0 else "BUY"
                    order = await self.binance_client.place_market_order(symbol, side, abs(current_amt), reduce_only=True)
                    logger.info("Closed Position")
                    await self._broadcast_trade("CLOSE", symbol, abs(current_amt), order)
                    
                    # Calculate PnL (Estimated)
                    # Robust Price Extraction
                    exit_price = float(order.get('avgPrice', 0) or order.get('price', 0))
                    if exit_price == 0 and 'fills' in order and order['fills']:
                        exit_price = sum(float(f['price']) * float(f['qty']) for f in order['fills']) / sum(float(f['qty']) for f in order['fills'])
                    if exit_price == 0:
                        exit_price = price # Use the price passed to _execute_order as fallback
                    
                    # Extract Commission
                    commission = 0.0
                    if 'fills' in order and order['fills']:
                        commission = sum(float(f.get('commission', 0)) for f in order['fills'])

                    # --- CIRCUIT BREAKER RECORDING ---
                    # Need PnL percentage roughly.
                    # cost = entry_price * amount
                    cost_basis = float(position['entry_price']) * abs(current_amt)
                    pnl_val = 0.0
                    
                    entry_price = float(position['entry_price'])
                    if side == "SELL": # Long Close
                        pnl_val = (exit_price - entry_price) * abs(current_amt)
                    else: # Short Close
                        pnl_val = (entry_price - exit_price) * abs(current_amt)
                        
                    if cost_basis > 0:
                        pnl_pct = (pnl_val / cost_basis) * 100
                        self.circuit_breaker.record_trade(pnl_pct)
                    # ---------------------------------

                    entry_price = float(position['entry_price'])
                    if side == "SELL": # Long Close
                        pnl = (exit_price - entry_price) * abs(current_amt)
                    else: # Short Close
                        pnl = (entry_price - exit_price) * abs(current_amt)
                        
                    await self._save_trade_to_db(symbol, "CLOSE", side, abs(current_amt), exit_price, pnl, "ai_ppo", commission=commission)

            # For Open Actions (LONG/SHORT)
            if action in [1, 2] and 'order' in locals():
                 side = "BUY" if action == 1 else "SELL"
                 action_str = "LONG" if action == 1 else "SHORT"
                 
                 # --- DYNAMIC ATR STOP LOSS CALCULATION ---
                 if atr > 0:
                     sl_multiplier = 2.0
                     # Phase 2 TODO: Adjust multiplier based on volatility regime
                     
                     sl_price = 0.0
                     if action == 1: # LONG
                         sl_price = price - (atr * sl_multiplier)
                     else: # SHORT
                         sl_price = price + (atr * sl_multiplier)
                         
                     logger.info(f"Dynamic SL Strategy: Recommending SL @ {sl_price:.2f} (ATR: {atr:.2f}, Mult: {sl_multiplier})")
                 else:
                     logger.warning("Dynamic SL Strategy: ATR is 0, cannot calculate safe stop loss.")
                 # ----------------------------------------
                 
                 # Robust Price Extraction for Open
                 avg_price = float(order.get('avgPrice', 0) or order.get('price', 0))
                 if avg_price == 0 and 'fills' in order and order['fills']:
                     avg_price = sum(float(f['price']) * float(f['qty']) for f in order['fills']) / sum(float(f['qty']) for f in order['fills'])
                 if avg_price == 0:
                     avg_price = price # Use the price passed to _execute_order as fallback
                 
                 # Extract Commission for Open
                 commission = 0.0
                 if 'fills' in order and order['fills']:
                     commission = sum(float(f.get('commission', 0)) for f in order['fills'])

                 await self._save_trade_to_db(
                     symbol=symbol,
                     action=action_str,
                     side=side,
                     quantity=quantity,
                     price=avg_price,
                     pnl=0.0, # Opening capability, PnL is 0
                     strategy="ai_ppo",
                     commission=commission
                 )

        except Exception as e:
            logger.error(f"Order Execution Failed: {e}")

    async def _execute_shadow_trade(self, symbol: str, action: int, price: float):
        """Execute virtual trade for shadow mode"""
        port = self.shadow_portfolio
        current_amt = port['position_amt']
        quantity = 0.001 # BTC fixed for shadow too for fair comparison
        if symbol != "BTCUSDT": quantity = 1
        
        commission_rate = 0.0004
        action_name = "HOLD"
        
        if action == 1: # LONG
            if current_amt <= 0:
                if current_amt < 0: # Close short
                    pnl = (port['entry_price'] - price) * abs(current_amt)
                    cost = abs(current_amt) * price * commission_rate
                    port['balance'] += pnl - cost
                    port['position_amt'] = 0
                    port['total_trades'] += 1
                    if pnl > cost: port['win_trades'] += 1
                
                # Open long
                cost = quantity * price * commission_rate
                port['balance'] -= cost
                port['position_amt'] = quantity
                port['entry_price'] = price
                action_name = "LONG"
                
        elif action == 2: # SHORT
             if current_amt >= 0:
                if current_amt > 0: # Close long
                    pnl = (price - port['entry_price']) * abs(current_amt)
                    cost = abs(current_amt) * price * commission_rate
                    port['balance'] += pnl - cost
                    port['position_amt'] = 0
                    port['total_trades'] += 1
                    if pnl > cost: port['win_trades'] += 1
                
                # Open short
                cost = quantity * price * commission_rate
                port['balance'] -= cost
                port['position_amt'] = -quantity
                port['entry_price'] = price
                action_name = "SHORT"

        elif action == 3: # CLOSE
            if current_amt != 0:
                pnl = 0
                if current_amt > 0: pnl = (price - port['entry_price']) * abs(current_amt)
                else: pnl = (port['entry_price'] - price) * abs(current_amt)
                
                cost = abs(current_amt) * price * commission_rate
                port['balance'] += pnl - cost
                port['position_amt'] = 0
                port['total_trades'] += 1
                if pnl > cost: port['win_trades'] += 1
                action_name = "CLOSE"
        
        # Update unrealized PnL
        if port['position_amt'] != 0:
            if port['position_amt'] > 0:
                port['unrealized_pnl'] = (price - port['entry_price']) * abs(port['position_amt'])
            else:
                port['unrealized_pnl'] = (port['entry_price'] - price) * abs(port['position_amt'])
        else:
            port['unrealized_pnl'] = 0
            
        if action_name != "HOLD":
             logger.info(f"Shadow Trade {action_name} @ {price:.2f} | Bal: {port['balance']:.2f}")
             self._broadcast_shadow_update(action_name, price)
             
    def _broadcast_shadow_update(self, action: str, price: float):
        """Broadcast shadow output"""
        if self.ws_manager:
            asyncio.create_task(self.ws_manager.broadcast({
                "type": "shadow_trade",
                "action": action,
                "price": price,
                "portfolio": self.shadow_portfolio,
                "timestamp": int(datetime.now().timestamp() * 1000)
            }, channel="trades"))

    async def _broadcast_trade(self, action: str, symbol: str, quantity: float, order: Dict):
        """Broadcast trade event to frontend"""
        if self.ws_manager:
            data = {
                "type": "trade",
                "action": action,
                "symbol": symbol,
                "quantity": quantity,
                "price": float(order.get('avgPrice', 0) or order.get('price', 0) or 0), # Handle various API responses
                "timestamp": int(datetime.now().timestamp() * 1000)
            }
            await self.ws_manager.broadcast(data, channel="trades")

    async def _save_trade_to_db(self, symbol: str, action: str, side: str, 
                               quantity: float, price: float, 
                               pnl: float = 0.0, strategy: str = "ai_ppo", reason: str = None,
                               commission: float = 0.0):
        """Log trade to database"""
        try:
            from app.database import SessionLocal
            from app.models import Trade
            
            async with SessionLocal() as session:
                trade = Trade(
                    symbol=symbol,
                    action=action,
                    side=side,
                    quantity=quantity,
                    price=price,
                    pnl=pnl,
                    commission=commission,
                    strategy=strategy,
                    reason=reason
                )
                session.add(trade)
                await session.commit()
                # logger.debug(f"Saved trade {action} {symbol} @ {price}")
        except Exception as e:
            logger.error(f"Failed to save trade to DB: {e}")
