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
from app.services.notifications import notification_manager, NotificationType
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
        self.last_heartbeat_ts = 0

        # Notification / Stats
        self.bot_start_balance: Optional[float] = None
        self.trade_stats = {"total": 0, "wins": 0}
        self.last_trade_ts: float = 0.0
        self.position_open_ts: dict[str, float] = {}
        # Track per-symbol bracket orders (TP/SL)
        # { "BTCUSDT": {"side":"LONG","qty":0.01,"entry_price":65000,"tp":66000,"sl":64500,"tp_order_id":123,"sl_order_id":456,"entry_ts":...}}
        self.brackets: dict[str, Dict] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._daily_report_task: Optional[asyncio.Task] = None
        self._last_error_notify_ts: float = 0.0
        self._last_error_msg: str = ""
        
        # Risk Management
        self.risk_config = RiskConfig()
        self.strategy_config = StrategyConfig() # New Config
        # 🔧 REMOVED: allowed_symbols restriction - now using coin_selector dynamically
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
        
        # 🔧 FIX: Remove allowed_symbols restriction - use coin_selector instead
        # This was blocking all trading signals!
        
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
            if self.bot_start_balance is None:
                self.bot_start_balance = account['balance']
            self.current_daily_loss = 0.0
            self.risk_status = "NORMAL"
            logger.info(f"Risk Monitor Initialized. Start Balance: ${self.daily_start_balance:.2f}")
        except Exception as e:
            logger.error(f"Failed to init risk monitor: {e}")
            
        self.running = True
        logger.info("Auto Trading Started")

        # Background notifications (heartbeat + daily report)
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        if self._daily_report_task is None or self._daily_report_task.done():
            self._daily_report_task = asyncio.create_task(self._daily_report_loop())

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
        for t in (self._heartbeat_task, self._daily_report_task):
            if t and not t.done():
                t.cancel()
        self._heartbeat_task = None
        self._daily_report_task = None
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

        # 🔧 FIX: Check coin_selector instead of hard-coded allowed_symbols
        # This allows dynamic coin selection
        symbol = data.get('symbol')
        
        # --- HEARTBEAT LOG ---
        # Log every 60 seconds to show user the bot is alive and detailed status
        now = time.time()
        if now - self.last_heartbeat_ts > 60:
            self.last_heartbeat_ts = now
            price = float(data.get('close', 0))
            
            # 🔧 Enhanced logging
            selected = await coin_selector.get_selected_coins()
            logger.info(f"👀 Scanning Market... {symbol} @ ${price:.2f} | Selected coins: {len(selected)} ({', '.join(selected)}) | Running: {self.running}")
        # ---------------------
        
        selected_coins = await coin_selector.get_selected_coins()
        if symbol not in selected_coins:
            # Only log every 60s if not selected to avoid spam
            if now - self.last_heartbeat_ts > 60:
                logger.debug(f"⏭️ Skipping {symbol} (not in selected: {selected_coins})")
            return
        
        # Log when we actually get data for a selected coin
        if now - self.last_heartbeat_ts > 60:
            logger.debug(f"📥 Received data for {symbol} (is_closed: {data.get('is_closed')})")

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
                await self._notify_error(f"AutoTrading error: {e}", context={"symbol": data.get("symbol")})
            finally:
                self.processing = False

    async def _trade_logic(self, data: Dict):
        """Core trading logic"""
        symbol = data['symbol']
        
        # 🔧 Note: Symbol already checked in process_market_data, no need to check again
        # This was causing double-filtering
        
        # 1. Get current position
        position = await self.binance_client.get_position(symbol)
        if position is None:
            logger.warning(f"Could not fetch position for {symbol}, skipping trade logic.")
            return

        # Detect external close (TP/SL/manual) between candles: previously had position, now flat.
        try:
            prev_br = self.brackets.get(symbol)
            current_amt = float(position.get("position_amt", 0))
            if prev_br and current_amt == 0:
                await self._handle_external_close(symbol=symbol, prev_bracket=prev_br, current_price=float(data.get("close", 0)))
        except Exception:
            pass

        # Track position open time (best-effort)
        try:
            amt = float(position.get("position_amt", 0))
            if amt != 0 and symbol not in self.position_open_ts:
                self.position_open_ts[symbol] = time.time()
            if amt == 0 and symbol in self.position_open_ts:
                del self.position_open_ts[symbol]
        except Exception:
            pass
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
        logger.info(f"🔄 Trading Mode: {self.strategy_config.mode} | Interval: {trading_interval} | Symbol: {symbol}")
        df = await self.binance_client.get_klines(symbol, interval=trading_interval, limit=300)
        
        # 🔧 Validate data
        if df is None or len(df) < 50:
            logger.warning(f"⚠️ Insufficient data for {symbol}: {len(df) if df is not None else 0} candles")
            return
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
        
        # --- RICH HEARTBEAT / ANALYSIS LOG ---
        # Log analysis details periodically (e.g. every 5 mins) or on every candle if user wants "verbose"
        # We'll log concise analysis every candle since user asked for "24 indicators logic logs"
        
        # Format key indicators
        rsi_val = market_state.get('rsi', 0)
        stoch_k = market_state.get('stoch_k_mid', 0) # Using Mid term
        trend = "BULL" if market_state.get('ema_21', 0) > market_state.get('ema_50', 0) else "BEAR"
        
        analysis_msg = (
            f"📊 Analysis {symbol}: "
            f"RSI={rsi_val:.1f} | "
            f"Stoch(Mid)={stoch_k:.1f} | "
            f"Trend={trend} | "
            f"Regime={current_regime}"
        )
        logger.info(analysis_msg)
        # -------------------------------------
        
        # 4. AI Prediction (AI acts as FILTER/VALIDATOR)
        ai_action = self.agent.live_predict(market_state)
        ai_action_name = ["HOLD", "LONG", "SHORT", "CLOSE"][ai_action]
        
        # 5. Tech Signal (Rules are the CAPTAIN)
        logger.info(f"🔍 Checking technical signals for {symbol}...")
        tech_signal = self.stoch_strategy.should_enter(df)
        
        if tech_signal:
            logger.info(f"✅ Tech Signal Found: {tech_signal['action']} | Strength: {tech_signal['strength']} | Reason: {tech_signal['reason']}")
        else:
            logger.debug(f"⏸️ No tech signal for {symbol}")
        
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
        logger.info(f"🎯 DECISION {symbol} - AI: {ai_action_name} | Rule: {tech_signal['action'] if tech_signal else 'None'} -> Final: {final_action_str} ({reason})")
        
        # 5. Execute Order (Main)
        await self._execute_order(
            symbol=symbol,
            action=final_action,
            position=position,
            price=float(latest['close']),
            atr=float(market_state.get('atr', 0)),
            reason=reason,
            leverage=int(leverage),
            market_state=market_state
        )

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

    async def _execute_order(
        self,
        symbol: str,
        action: int,
        position: Dict,
        price: float,
        atr: float = 0.0,
        reason: str = "",
        leverage: int = 5,
        market_state: Optional[Dict] = None,
    ):
        """Execute order based on action"""
        current_amt = position['position_amt']
        
        async def _round_quantity(sym: str, qty: float):
            try:
                # 1. Fetch exchange info for precision
                info = await self.binance_client.get_exchange_info()
                if not info or 'symbols' not in info:
                    return round(qty, 3) # Hand-wave fallback
                
                # 2. Find symbol
                s_info = next((s for s in info['symbols'] if s['symbol'] == sym), None)
                if not s_info:
                    return round(qty, 3)
                
                # 3. Get precision (quantityPrecision)
                precision = int(s_info.get('quantityPrecision', 3))
                
                # 4. Standard Round Down
                import math
                factor = 10 ** precision
                return math.floor(qty * factor) / factor
            except:
                return round(qty, 3)

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

        quantity = await _round_quantity(symbol, quantity)
            
        try:
            if action == 1: # LONG
                if current_amt <= 0: # If short or flat
                    if current_amt < 0: # Close short first
                        close_order = await self.binance_client.place_market_order(symbol, "BUY", abs(current_amt), reduce_only=True)
                        await self._handle_close_notification(
                            symbol=symbol,
                            position=position,
                            close_order=close_order,
                            fallback_price=price,
                            reason=f"FLIP_TO_LONG|{reason}".strip("|"),
                        )
                    # Open long
                    order = await self.binance_client.place_market_order(symbol, "BUY", quantity)
                    logger.info("Executed LONG")
                    await self._broadcast_trade("LONG", symbol, quantity, order)
                    entry_price, tp_price, sl_price = await self._setup_bracket_after_entry(
                        symbol=symbol,
                        side="LONG",
                        quantity=quantity,
                        leverage=leverage,
                        order=order,
                        fallback_price=price,
                        atr=atr,
                        market_state=market_state or {},
                        reason=reason,
                    )
                    await self._handle_entry_notification(
                        symbol=symbol,
                        side="LONG",
                        quantity=quantity,
                        leverage=leverage,
                        order=order,
                        fallback_price=price,
                        atr=atr,
                        reason=reason,
                        market_state=market_state or {},
                        tp_price=tp_price,
                        sl_price=sl_price,
                    )
                    
            elif action == 2: # SHORT
                if current_amt >= 0: # If long or flat
                    if current_amt > 0: # Close long first
                         close_order = await self.binance_client.place_market_order(symbol, "SELL", abs(current_amt), reduce_only=True)
                         await self._handle_close_notification(
                             symbol=symbol,
                             position=position,
                             close_order=close_order,
                             fallback_price=price,
                             reason=f"FLIP_TO_SHORT|{reason}".strip("|"),
                         )
                    # Open short
                    order = await self.binance_client.place_market_order(symbol, "SELL", quantity)
                    logger.info("Executed SHORT")
                    await self._broadcast_trade("SHORT", symbol, quantity, order)
                    entry_price, tp_price, sl_price = await self._setup_bracket_after_entry(
                        symbol=symbol,
                        side="SHORT",
                        quantity=quantity,
                        leverage=leverage,
                        order=order,
                        fallback_price=price,
                        atr=atr,
                        market_state=market_state or {},
                        reason=reason,
                    )
                    await self._handle_entry_notification(
                        symbol=symbol,
                        side="SHORT",
                        quantity=quantity,
                        leverage=leverage,
                        order=order,
                        fallback_price=price,
                        atr=atr,
                        reason=reason,
                        market_state=market_state or {},
                        tp_price=tp_price,
                        sl_price=sl_price,
                    )
                    
            elif action == 3: # CLOSE
                if current_amt != 0:
                    side = "SELL" if current_amt > 0 else "BUY"
                    order = await self.binance_client.place_market_order(symbol, side, abs(current_amt), reduce_only=True)
                    logger.info("Closed Position")
                    await self._broadcast_trade("CLOSE", symbol, abs(current_amt), order)
                    await self._handle_close_notification(
                        symbol=symbol,
                        position=position,
                        close_order=order,
                        fallback_price=price,
                        reason=reason,
                    )
                    
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
                        
                    await self._save_trade_to_db(symbol, "CLOSE", side, abs(current_amt), exit_price, pnl, "ai_ppo", reason=reason, commission=commission)

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
                      reason=reason,
                     commission=commission
                 )

        except Exception as e:
            logger.error(f"Order Execution Failed: {e}")
            await self._notify_error(f"Order Execution Failed: {e}", context={"symbol": symbol, "action": action})

    # -----------------------------
    # Notifications (Telegram)
    # -----------------------------
    def _fmt_symbol(self, symbol: str) -> str:
        if symbol.endswith("USDT") and len(symbol) > 4:
            return f"{symbol[:-4]}/USDT"
        return symbol

    def _fmt_usdt(self, x: float) -> str:
        try:
            return f"{x:,.2f}"
        except Exception:
            return str(x)

    def _fmt_qty(self, symbol: str, qty: float) -> str:
        if symbol.endswith("USDT"):
            base = symbol[:-4]
        else:
            base = symbol
        # BTC is usually 3 decimals in this project
        if base.upper() == "BTC":
            return f"{qty:.3f} {base}"
        return f"{qty:.4f} {base}"

    def _format_duration(self, seconds: float) -> str:
        seconds = max(0, int(seconds))
        h = seconds // 3600
        m = (seconds % 3600) // 60
        if h > 0:
            return f"{h}시간 {m}분"
        return f"{m}분"

    async def _notify_error(self, message: str, context: Optional[Dict] = None):
        # Throttle error notifications (avoid spam)
        now = time.time()
        if message == self._last_error_msg and (now - self._last_error_notify_ts) < 300:
            return
        self._last_error_msg = message
        self._last_error_notify_ts = now

        if not notification_manager.enabled_channels.get("telegram", False):
            return
        try:
            ctx = ""
            if context and context.get("symbol"):
                ctx = f" ({context.get('symbol')})"
            await notification_manager.send(
                NotificationType.SYSTEM_ERROR,
                "System Error",
                f"🚨 <b>[에러]</b>{ctx}\n{message}",
                channels=["telegram"],
            )
        except Exception:
            # don't crash trading on notification failures
            pass

    async def _handle_entry_notification(
        self,
        symbol: str,
        side: str,
        quantity: float,
        leverage: int,
        order: Dict,
        fallback_price: float,
        atr: float,
        reason: str,
        market_state: Dict,
        tp_price: float | None = None,
        sl_price: float | None = None,
    ):
        if not notification_manager.enabled_channels.get("telegram", False):
            return

        # Robust avg price
        avg_price = float(order.get("avgPrice", 0) or order.get("price", 0) or 0)
        if avg_price == 0 and order.get("fills"):
            fills = order["fills"]
            avg_price = sum(float(f["price"]) * float(f["qty"]) for f in fills) / max(1e-9, sum(float(f["qty"]) for f in fills))
        if avg_price == 0:
            avg_price = float(fallback_price)

        # Track open time for hold duration
        self.position_open_ts[symbol] = time.time()
        self.last_trade_ts = time.time()

        s = self._fmt_symbol(symbol)
        emoji = "🟢" if side == "LONG" else "🔴"
        notional = avg_price * float(quantity)
        tp_sl = ""
        if tp_price and sl_price:
            tp_sl = f"목표가: {self._fmt_usdt(tp_price)} / 손절가: {self._fmt_usdt(sl_price)}"
        elif tp_price:
            tp_sl = f"목표가: {self._fmt_usdt(tp_price)}"
        elif sl_price:
            tp_sl = f"손절가: {self._fmt_usdt(sl_price)}"

        msg = (
            f"🚀 <b>[진입]</b> {s} 포지션: {emoji} <b>{side}</b> ({leverage}x)\n"
            f"진입가: <b>{self._fmt_usdt(avg_price)}</b> USDT\n"
            f"수량: <b>{self._fmt_qty(symbol, float(quantity))}</b> (약 {self._fmt_usdt(notional)} USDT)\n"
        )
        if tp_sl:
            msg += f"{tp_sl}\n"
        if reason:
            msg += f"사유: <code>{reason}</code>"

        try:
            await notification_manager.send(NotificationType.TRADE_EXECUTED, "Entry", msg, channels=["telegram"])
        except Exception as e:
            await self._notify_error(f"Telegram entry notify failed: {e}", context={"symbol": symbol})

    async def _setup_bracket_after_entry(
        self,
        symbol: str,
        side: str,
        quantity: float,
        leverage: int,
        order: Dict,
        fallback_price: float,
        atr: float,
        market_state: Dict,
        reason: str,
    ) -> tuple[float, float | None, float | None]:
        """Compute TP/SL and place reduce-only bracket orders. Returns (entry_price, tp_price, sl_price)."""
        # avg entry price
        entry_price = float(order.get("avgPrice", 0) or order.get("price", 0) or 0)
        if entry_price == 0 and order.get("fills"):
            fills = order["fills"]
            entry_price = sum(float(f["price"]) * float(f["qty"]) for f in fills) / max(1e-9, sum(float(f["qty"]) for f in fills))
        if entry_price == 0:
            entry_price = float(fallback_price)

        tp_price: float | None = None
        sl_price: float | None = None
        try:
            pos_amt = quantity if side == "LONG" else -quantity
            sltp = self.sl_tp_ai.get_sl_tp_for_position(
                position={"entry_price": entry_price, "position_amt": pos_amt, "unrealized_pnl": 0.0},
                current_market_data={
                    "close": entry_price,
                    "atr": float(atr),
                    "rsi": float(market_state.get("rsi", 50.0)),
                    "macd": float(market_state.get("macd", 0.0)),
                },
            )
            sl_price = float(sltp.get("sl_price")) if sltp.get("sl_price") is not None else None
            tp_price = float(sltp.get("tp_price")) if sltp.get("tp_price") is not None else None
        except Exception as e:
            await self._notify_error(f"SL/TP compute failed: {e}", context={"symbol": symbol})

        # Place bracket orders (best-effort)
        try:
            res = await self.binance_client.place_bracket_orders(
                symbol=symbol,
                position_side=side,
                quantity=float(quantity),
                stop_loss_price=sl_price,
                take_profit_price=tp_price,
            )
            self.brackets[symbol] = {
                "symbol": symbol,
                "side": side,
                "qty": float(quantity),
                "leverage": int(leverage),
                "entry_price": float(entry_price),
                "tp": float(tp_price) if tp_price is not None else None,
                "sl": float(sl_price) if sl_price is not None else None,
                "tp_order_id": (res.get("tp") or {}).get("orderId") if res.get("tp") else None,
                "sl_order_id": (res.get("sl") or {}).get("orderId") if res.get("sl") else None,
                "entry_ts": time.time(),
                "entry_reason": reason,
            }
        except Exception as e:
            await self._notify_error(f"Bracket order placement failed: {e}", context={"symbol": symbol})

        return entry_price, tp_price, sl_price

    async def _handle_external_close(self, symbol: str, prev_bracket: Dict, current_price: float):
        """
        If a position is closed by exchange (TP/SL/manual) we won't see a CLOSE action.
        Infer reason and notify + cleanup open orders.
        """
        # Attempt to infer exit price & pnl from recent trades (best-effort)
        reason = "EXTERNAL_CLOSE"
        tp = prev_bracket.get("tp")
        sl = prev_bracket.get("sl")
        side = prev_bracket.get("side")

        # Rough infer by proximity to tp/sl
        try:
            if tp and side == "LONG" and current_price >= float(tp) * 0.999:
                reason = "TP"
            elif tp and side == "SHORT" and current_price <= float(tp) * 1.001:
                reason = "TP"
            elif sl and side == "LONG" and current_price <= float(sl) * 1.001:
                reason = "SL"
            elif sl and side == "SHORT" and current_price >= float(sl) * 0.999:
                reason = "SL"
        except Exception:
            pass

        # Cancel any remaining open orders
        try:
            await self.binance_client.cancel_open_orders(symbol)
        except Exception:
            pass

        # Save to DB (estimated) + Notify as a synthetic close (we don't have exact exit fill here)
        try:
            entry_price = float(prev_bracket.get("entry_price", 0) or 0)
            qty = float(prev_bracket.get("qty", 0) or 0)
            lev = int(prev_bracket.get("leverage", 1) or 1)
            if qty > 0 and entry_price > 0:
                if side == "LONG":
                    pnl = (current_price - entry_price) * qty
                else:
                    pnl = (entry_price - current_price) * qty
                roe = ((pnl * lev) / (entry_price * qty)) * 100.0 if entry_price * qty > 0 else 0.0
            else:
                pnl = 0.0
                roe = 0.0

            try:
                close_side = "SELL" if side == "LONG" else "BUY"
                await self._save_trade_to_db(
                    symbol=symbol,
                    action="CLOSE",
                    side=close_side,
                    quantity=qty,
                    price=float(current_price),
                    pnl=float(pnl),
                    strategy="ai_ppo",
                    reason=reason,
                    commission=0.0,
                )
            except Exception:
                pass

            hold = None
            if symbol in self.position_open_ts:
                hold = self._format_duration(time.time() - self.position_open_ts[symbol])
                del self.position_open_ts[symbol]

            s = self._fmt_symbol(symbol)
            emoji = "💰" if pnl >= 0 else "🔻"
            label = "익절" if reason == "TP" else ("손절" if reason == "SL" else "청산")
            msg = (
                f"{emoji} <b>[{label}]</b> {s}\n"
                f"종료가(추정): <b>{self._fmt_usdt(current_price)}</b> USDT\n"
                f"실현손익(추정): <b>{pnl:+.2f}</b> USDT\n"
                f"수익률(ROE,추정): <b>{roe:+.2f}%</b>\n"
            )
            if hold:
                msg += f"보유시간: {hold}\n"
            msg += f"종료사유: <code>{reason}</code>"
            if notification_manager.enabled_channels.get("telegram", False):
                await notification_manager.send(NotificationType.POSITION_CLOSED, "Exit", msg, channels=["telegram"])
        except Exception:
            pass

        # Cleanup bracket state
        try:
            if symbol in self.brackets:
                del self.brackets[symbol]
        except Exception:
            pass
    async def _handle_close_notification(
        self,
        symbol: str,
        position: Dict,
        close_order: Dict,
        fallback_price: float,
        reason: str,
    ):
        current_amt = float(position.get("position_amt", 0))
        if current_amt == 0:
            return

        entry_price = float(position.get("entry_price", 0) or 0)
        lev = int(position.get("leverage", 1) or 1)

        exit_price = float(close_order.get("avgPrice", 0) or close_order.get("price", 0) or 0)
        if exit_price == 0 and close_order.get("fills"):
            fills = close_order["fills"]
            exit_price = sum(float(f["price"]) * float(f["qty"]) for f in fills) / max(1e-9, sum(float(f["qty"]) for f in fills))
        if exit_price == 0:
            exit_price = float(fallback_price)

        commission = 0.0
        if close_order.get("fills"):
            commission = sum(float(f.get("commission", 0)) for f in close_order["fills"])

        qty = abs(current_amt)
        side_str = "LONG" if current_amt > 0 else "SHORT"
        close_side = "SELL" if current_amt > 0 else "BUY"
        if current_amt > 0:
            pnl = (exit_price - entry_price) * qty
        else:
            pnl = (entry_price - exit_price) * qty
        net_pnl = pnl - commission
        cost_basis = entry_price * qty
        roe = 0.0
        if cost_basis > 0 and lev > 0:
            roe = (pnl * lev / cost_basis) * 100.0

        # holding time
        now = time.time()
        hold = None
        if symbol in self.position_open_ts:
            hold = self._format_duration(now - self.position_open_ts[symbol])
            del self.position_open_ts[symbol]
        self.last_trade_ts = now

        # update stats
        self.trade_stats["total"] += 1
        if net_pnl > 0:
            self.trade_stats["wins"] += 1

        # Save to DB (also covers flip-closes which previously weren't recorded)
        try:
            await self._save_trade_to_db(
                symbol=symbol,
                action="CLOSE",
                side=close_side,
                quantity=qty,
                price=exit_price,
                pnl=pnl,
                strategy="ai_ppo",
                reason=reason,
                commission=commission,
            )
        except Exception:
            pass

        # Cancel remaining TP/SL orders for this symbol after closing the position
        try:
            await self.binance_client.cancel_open_orders(symbol)
        except Exception:
            pass

        # Cleanup bracket state
        try:
            if symbol in self.brackets:
                del self.brackets[symbol]
        except Exception:
            pass

        # reason label
        label = "청산"
        if "TP" in (reason or "").upper():
            label = "익절"
        elif "SL" in (reason or "").upper() or "STOP" in (reason or "").upper():
            label = "손절"

        s = self._fmt_symbol(symbol)
        pnl_sign = "+" if net_pnl >= 0 else ""
        roe_sign = "+" if roe >= 0 else ""
        emoji = "💰" if net_pnl >= 0 else "🔻"
        msg = (
            f"{emoji} <b>[{label}]</b> {s}\n"
            f"종료가: <b>{self._fmt_usdt(exit_price)}</b> USDT\n"
            f"실현손익: <b>{pnl_sign}{self._fmt_usdt(net_pnl)}</b> USDT\n"
            f"수익률(ROE): <b>{roe_sign}{roe:.2f}%</b>\n"
        )
        if hold:
            msg += f"보유시간: {hold}\n"
        if reason:
            msg += f"종료사유: <code>{reason}</code>\n"

        # Append quick risk summary (best effort)
        try:
            account = await self.binance_client.get_account_info()
            bal = float(account.get("balance", 0))
            daily_pnl = bal - float(self.daily_start_balance or bal)
            margin_ratio = 0.0
            mb = float(account.get("margin_balance", 0) or 0)
            mm = float(account.get("maint_margin", 0) or 0)
            if mb > 0:
                margin_ratio = (mm / mb) * 100.0
            wr = (self.trade_stats["wins"] / self.trade_stats["total"] * 100.0) if self.trade_stats["total"] > 0 else 0.0
            msg += (
                f"\n📊 <b>[요약]</b> 잔고: <b>{self._fmt_usdt(bal)}</b> USDT | "
                f"오늘: {daily_pnl:+.2f} USDT | 승률: {wr:.1f}% | 마진비율: {margin_ratio:.2f}%"
            )
        except Exception:
            pass

        if notification_manager.enabled_channels.get("telegram", False):
            try:
                await notification_manager.send(NotificationType.POSITION_CLOSED, "Exit", msg, channels=["telegram"])
            except Exception as e:
                await self._notify_error(f"Telegram exit notify failed: {e}", context={"symbol": symbol})

    async def _heartbeat_loop(self):
        """Send heartbeat every ~6 hours to confirm bot is alive."""
        try:
            while self.running:
                await asyncio.sleep(6 * 3600)
                if not self.running:
                    break
                if not notification_manager.enabled_channels.get("telegram", False):
                    continue
                now = time.time()
                last_trade = "없음"
                if self.last_trade_ts:
                    last_trade = self._format_duration(now - self.last_trade_ts) + " 전"
                msg = (
                    "🫀 <b>[Heartbeat]</b> 봇 정상 작동 중. 대기/모니터링 중...\n"
                    f"모드: <b>{self.strategy_config.mode}</b> | TF: <b>{self.strategy_config.selected_interval}</b>\n"
                    f"마지막 거래: {last_trade}"
                )
                await notification_manager.send(NotificationType.PRICE_ALERT, "Heartbeat", msg, channels=["telegram"])
        except asyncio.CancelledError:
            return
        except Exception as e:
            await self._notify_error(f"Heartbeat loop failed: {e}")

    async def _daily_report_loop(self):
        """Send daily report at 09:00 local time."""
        try:
            while self.running:
                now_dt = datetime.now()
                next_dt = now_dt.replace(hour=9, minute=0, second=0, microsecond=0)
                if next_dt <= now_dt:
                    next_dt = next_dt + timedelta(days=1)
                await asyncio.sleep((next_dt - now_dt).total_seconds())
                if not self.running:
                    break
                await self._send_daily_report()
        except asyncio.CancelledError:
            return
        except Exception as e:
            await self._notify_error(f"Daily report loop failed: {e}")

    async def _send_daily_report(self):
        if not notification_manager.enabled_channels.get("telegram", False):
            return
        try:
            account = await self.binance_client.get_account_info()
            bal = float(account.get("balance", 0))
            if self.bot_start_balance is None:
                self.bot_start_balance = bal
            daily_pnl = bal - float(self.daily_start_balance or bal)
            cum_ret = 0.0
            if self.bot_start_balance:
                cum_ret = ((bal - self.bot_start_balance) / self.bot_start_balance) * 100.0
            wr = (self.trade_stats["wins"] / self.trade_stats["total"] * 100.0) if self.trade_stats["total"] > 0 else 0.0
            mb = float(account.get("margin_balance", 0) or 0)
            mm = float(account.get("maint_margin", 0) or 0)
            margin_ratio = (mm / mb) * 100.0 if mb > 0 else 0.0

            msg = (
                "📊 <b>[일일 리포트]</b>\n"
                f"현재 잔고: <b>{self._fmt_usdt(bal)}</b> USDT\n"
                f"오늘 손익: <b>{daily_pnl:+.2f}</b> USDT\n"
                f"누적 수익률: <b>{cum_ret:+.2f}%</b>\n"
                f"승률: <b>{wr:.1f}%</b> ({self.trade_stats['wins']}승 {self.trade_stats['total']-self.trade_stats['wins']}패)\n"
                f"리스크(마진비율): <b>{margin_ratio:.2f}%</b>"
            )
            await notification_manager.send(NotificationType.PRICE_ALERT, "Daily Report", msg, channels=["telegram"])
        except Exception as e:
            await self._notify_error(f"Daily report send failed: {e}")
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
