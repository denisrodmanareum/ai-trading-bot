"""
Auto Trading Service
"""
import asyncio
from typing import Optional, Dict
from loguru import logger
from datetime import datetime, timedelta
import time

from trading.base_client import BaseExchangeClient
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
from ai.smart_money_concept import SmartMoneyConceptAnalyzer
from app.services.coin_selector import coin_selector
from trading.slippage_manager import SlippageManager  # 🆕
from trading.partial_exit_manager import PartialExitManager  # 🆕
from trading.trailing_sl_helper import move_sl_to_breakeven, update_trailing_stop_loss  # 🆕
from ai.portfolio_manager import PortfolioManager  # 🆕 Phase 2
from ai.crypto_vix import CryptoVIX  # 🆕 Phase 2
from ai.performance_monitor import PerformanceMonitor  # 🆕 Phase 2
from ai.hybrid_ai import HybridAI  # 🆕 Phase 3
from ai.backtest_engine import BacktestEngine  # 🆕 Phase 3
from ai.parameter_optimizer import ParameterOptimizer  # 🆕 Phase 3
from app.services.balance_strategy import BalanceBasedStrategyManager  # 🆕 잔고 기반 동적 전략
import os
import pandas as pd

class RiskConfig:
    """Risk Management Configuration"""
    def __init__(
        self, 
        daily_loss_limit=25.0,  # 🔧 50→25 USDT (잔고의 0.5%, 보수적 관리)
        max_margin_level=0.8, 
        kill_switch=False, 
        position_mode="ADAPTIVE",  # 🔧 "FIXED", "RATIO", "ADAPTIVE"
        position_ratio=0.03,  # Per coin ratio (기본 3%)
        max_total_exposure=0.26,  # 🔧 총 노출 26% (코어 20% + 알트 6%)
        core_coin_ratio=0.05,  # 🔧 NEW: 코어코인 비율 5%
        alt_coin_ratio=0.02   # 🔧 NEW: 알트코인 비율 2%
    ):
        self.daily_loss_limit = daily_loss_limit # USDT (현재 잔고 5000의 0.5%)
        self.max_margin_level = max_margin_level # Maintenance Margin / Margin Balance
        self.kill_switch = kill_switch # If True, no new trades allowed
        self.position_mode = position_mode # "FIXED", "RATIO", "ADAPTIVE"
        self.position_ratio = position_ratio # Per coin ratio (RATIO mode용)
        self.max_total_exposure = max_total_exposure # Total exposure limit
        self.core_coin_ratio = core_coin_ratio # 코어코인 배분 비율
        self.alt_coin_ratio = alt_coin_ratio # 알트코인 배분 비율
        # 코어코인 정의 (BTC, ETH, SOL, BNB)
        self.core_coins = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT']

class TrailingTakeProfitConfig:
    """Trailing Take Profit Configuration"""
    def __init__(
        self, 
        enabled=True,
        activation_pct=1.0,  # 트레일링 활성화 수익률
        distance_pct=1.2,    # 최고점에서 하락 허용치
        min_hold_minutes=15,  # 최소 보유시간 (기본값, 모드별로 조정됨)
        flip_min_signal_score=5  # FLIP 최소 신호 강도
    ):
        self.enabled = enabled
        self.activation_pct = activation_pct
        self.distance_pct = distance_pct
        self.min_hold_minutes = min_hold_minutes
        self.flip_min_signal_score = flip_min_signal_score
    
    def get_config_for_mode(self, mode: str) -> dict:
        """🔧 모드별 설정 반환 (수수료 고려)"""
        # 수수료: 0.04% × 2 = 0.08% (왕복)
        # FLIP 포함 시: 0.16% (4회 거래)
        # 레버리지 5x 적용 시: 수수료 영향 × 5
        
        if mode == "SCALP":
            return {
                'activation_pct': 2.0,  # 🔧 1.2→2.0% (더 큰 추세 추종)
                'distance_pct': 1.0,    # 🔧 0.8→1.0% (노이즈 허용 확대)
                'min_hold_minutes': 5,
                'flip_min_signal_score': 4
            }
        else:  # SWING
            return {
                'activation_pct': 4.0,  # 🔧 2.5→4.0% (스윙 수익 극대화)
                'distance_pct': 2.0,    # 🔧 1.5→2.0% (추세 끝까지 먹기)
                'min_hold_minutes': 60,
                'flip_min_signal_score': 5
            }

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
    
    def __init__(self, mode="SCALP", leverage_mode="AUTO", manual_leverage=5, autonomy_mode="AGGRESSIVE", selected_interval="15m", use_smc=False):
        self.mode = mode  # "SCALP" or "SWING"
        self.leverage_mode = leverage_mode  # "AUTO" or "MANUAL"
        self.manual_leverage = manual_leverage
        self.autonomy_mode = autonomy_mode  # "CONSERVATIVE" or "AGGRESSIVE"
        self.selected_interval = selected_interval  # Active trading interval
        self.use_smc = use_smc  # Smart Money Concept 전략 사용 여부
        
        # Strategy Parameters (Dynamic)
        self.parameters = {
            'oversold': 25,
            'overbought': 75,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'volume_spike_mult': 2.0
        }
    
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
    🔧 Enhanced 3-Tier Safety Mechanism
    - Tier 1: 15분 내 -1% → 5분 정지 (빠른 대응)
    - Tier 2: 30분 내 -2% → 30분 정지 (중간 위기)
    - Tier 3: 60분 내 -3% → 당일 거래 중단 (심각)
    """
    def __init__(self):
        # 🔧 3-Tier Configuration
        self.tiers = [
            {'window': 15, 'threshold': 1.0, 'pause': 5, 'name': 'MINOR'},    # Tier 1
            {'window': 30, 'threshold': 2.0, 'pause': 30, 'name': 'MODERATE'}, # Tier 2
            {'window': 60, 'threshold': 3.0, 'pause': 1440, 'name': 'SEVERE'}  # Tier 3 (24h)
        ]
        self.recent_losses = [] # List of (timestamp, loss_pct)
        self.paused_until: Optional[float] = None # Timestamp
        self.triggered_tier: Optional[str] = None

    def record_trade(self, pnl_pct: float):
        """Record trade result"""
        if pnl_pct < 0:
            self.recent_losses.append((time.time(), abs(pnl_pct)))
            # Clean up old records (older than max window)
            max_window = max(t['window'] for t in self.tiers)
            self._cleanup(max_window)
        
    def _cleanup(self, window_minutes: int):
        """Remove old records beyond window"""
        cutoff = time.time() - (window_minutes * 60)
        self.recent_losses = [x for x in self.recent_losses if x[0] > cutoff]
        
    def check_status(self) -> bool:
        """
        🔧 Check 3-tier circuit breaker status
        Returns: True if PAUSED (Safe mode), False if NORMAL
        """
        now = time.time()
        
        # 1. Check if already paused
        if self.paused_until and now < self.paused_until:
            remaining = (self.paused_until - now) / 60
            if int(remaining) % 5 == 0:  # Log every 5 minutes
                logger.warning(f"⏸️ Trading Paused ({self.triggered_tier}): {remaining:.0f}m remaining")
            return True
        elif self.paused_until:
            self.paused_until = None
            self.triggered_tier = None
            logger.info("✅ Circuit Breaker Lifted - Resuming Trading")

        # 2. 🔧 Check all tiers (from highest to lowest)
        for tier in reversed(self.tiers):  # Check Tier 3 → 2 → 1
            self._cleanup(tier['window'])
            
            # Calculate losses within window
            cutoff = now - (tier['window'] * 60)
            window_losses = [x[1] for x in self.recent_losses if x[0] > cutoff]
            total_loss_pct = sum(window_losses)
            
            if total_loss_pct >= tier['threshold']:
                self.paused_until = now + (tier['pause'] * 60)
                self.triggered_tier = tier['name']
                
                pause_desc = "24시간" if tier['pause'] >= 1440 else f"{tier['pause']}분"
                logger.critical(
                    f"🚨 CIRCUIT BREAKER [{tier['name']}] TRIGGERED! "
                    f"손실 {total_loss_pct:.2f}% in {tier['window']}분 "
                    f"(임계값: {tier['threshold']}%) → {pause_desc} 거래 정지"
                )
                return True
            
        return False

# Helper to get the correct exchange client
# Helper to get the correct exchange client
async def get_exchange_client():
    from trading.exchange_factory import ExchangeFactory
    return await ExchangeFactory.get_client()

class AutoTradingService:
    
    def __init__(self, exchange_client: BaseExchangeClient, ws_manager: WebSocketManager = None):
        self.exchange_client = exchange_client
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
        # 🔧 Track last trade time per symbol (prevent duplicate trades)
        self.last_trade_time_per_symbol: dict[str, float] = {}
        # Track per-symbol bracket orders (TP/SL)
        # { "BTCUSDT": {"side":"LONG","qty":0.01,"entry_price":65000,"tp":66000,"sl":64500,"tp_order_id":123,"sl_order_id":456,"entry_ts":...}}
        self.brackets: dict[str, Dict] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._daily_report_task: Optional[asyncio.Task] = None
        self._performance_monitor_task: Optional[asyncio.Task] = None  # 🆕
        self._last_error_notify_ts: float = 0.0
        self._last_error_msg: str = ""
        
        # Risk Management
        self.risk_config = RiskConfig()
        self.strategy_config = StrategyConfig() # New Config
        self.trailing_config = TrailingTakeProfitConfig() # Trailing Take Profit Config
        # 🔧 REMOVED: allowed_symbols restriction - now using coin_selector dynamically
        self.daily_start_balance = 0.0
        self.current_daily_loss = 0.0
        self.last_margin_level = 0.0
        self.risk_status = "NORMAL" # NORMAL, WARNING, STOPPED
        
        # Stochastic Strategy
        self.stoch_strategy = StochasticTradingStrategy(config=self.strategy_config.parameters)
        
        # Spike Detector
        self.spike_detector = SpikeDetector()
        
        # AI Components (NEW!)
        self.regime_detector = MarketRegimeDetector()
        self.position_sizer = PositionSizer()
        self.sl_tp_ai = StopLossTakeProfitAI()
        self.mtf_analyzer = MultiTimeframeAnalyzer(exchange_client)
        self.smc_analyzer = SmartMoneyConceptAnalyzer()
        
        # 🆕 Phase 1: Order Optimization
        self.slippage_manager = SlippageManager(self.exchange_client)
        self.partial_exit_manager = PartialExitManager()
        
        # 🆕 Phase 2: Risk Optimization
        self.portfolio_manager = PortfolioManager(self.exchange_client)
        self.crypto_vix = CryptoVIX(self.exchange_client)
        self.performance_monitor = PerformanceMonitor(self.exchange_client, self)
        
        # 🆕 Phase 3: AI Enhancement
        self.hybrid_ai = HybridAI()
        self.backtest_engine = BacktestEngine(self.exchange_client)
        self.parameter_optimizer = ParameterOptimizer(self.backtest_engine)
        
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
        
        # 🆕 Balance-Based Strategy Manager (잔고 티어 시스템)
        self.balance_strategy = BalanceBasedStrategyManager()
        logger.info("✅ Balance-Based Strategy Manager initialized")
        
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
                    
                    # 🆕 Hybrid AI 초기화
                    try:
                        self.hybrid_ai.ppo_agent = self.agent
                        self.hybrid_ai.mode = "ppo_only"
                        
                        # 최신 LSTM 모델 찾기 (현재 interval 기준)
                        import glob
                        symbol = "BTCUSDT" # Default or dynamic
                        interval = self.strategy_config.selected_interval
                        lstm_pattern = os.path.join(settings.AI_MODEL_PATH, f"lstm_{symbol}_{interval}_*.pt")
                        lstm_models = sorted(glob.glob(lstm_pattern))
                        
                        if lstm_models:
                            latest_lstm = lstm_models[-1]
                            self.hybrid_ai.load_lstm(latest_lstm)
                            logger.info(f"✅ Hybrid AI: LSTM model loaded for {interval}")
                        else:
                            logger.warning(f"⚠️ Hybrid AI: No LSTM model found for {interval}")
                    except Exception as he:
                        logger.error(f"Hybrid AI initialization failed: {he}")
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
            df = await self.exchange_client.get_klines("BTCUSDT", interval="1h", limit=1000)
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
            account = await self.exchange_client.get_account_info()
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
            
        # 🔧 Restore state from DB
        await self._load_state()
        
        # 🆕 Start performance monitoring loop
        if self._performance_monitor_task is None or self._performance_monitor_task.done():
            self._performance_monitor_task = asyncio.create_task(self._performance_monitor_loop())

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
        
    def update_risk_config(
        self, 
        daily_loss_limit=None, 
        max_margin_level=None, 
        kill_switch=None, 
        position_mode=None, 
        position_ratio=None,
        max_total_exposure=None,
        core_coin_ratio=None,  # 🔧 NEW
        alt_coin_ratio=None   # 🔧 NEW
    ):
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
            logger.info(f"📊 Position Mode Changed: {position_mode}")
        if position_ratio is not None:
            self.risk_config.position_ratio = position_ratio
        if max_total_exposure is not None:
            self.risk_config.max_total_exposure = max_total_exposure
            logger.info(f"📊 Max Total Exposure Changed: {max_total_exposure*100:.0f}%")
        if core_coin_ratio is not None:  # 🔧 NEW
            self.risk_config.core_coin_ratio = core_coin_ratio
            logger.info(f"📊 Core Coin Ratio Changed: {core_coin_ratio*100:.0f}%")
        if alt_coin_ratio is not None:  # 🔧 NEW
            self.risk_config.alt_coin_ratio = alt_coin_ratio
            logger.info(f"📊 Alt Coin Ratio Changed: {alt_coin_ratio*100:.0f}%")

    async def stop(self):
        """Stop auto trading"""
        self.running = False
        await self.stop_shadow_mode() # Stop shadow too
        
        # Cancel specific tasks
        for t in (self._heartbeat_task, self._daily_report_task, self._performance_monitor_task):
            if t and not t.done():
                t.cancel()
                try:
                    await t
                except asyncio.CancelledError:
                    pass
        
        self._heartbeat_task = None
        self._daily_report_task = None
        self._performance_monitor_task = None
        
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
                account = await self.exchange_client.get_account_info()
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
        
        # 🆕 일일 거래 제한 체크 (Balance-Based Strategy)
        try:
            account = await self.exchange_client.get_account_info()
            current_balance = account.get('balance', 5000.0)
            can_trade, limit_msg = self.balance_strategy.check_daily_trade_limit(current_balance)
            if not can_trade:
                logger.warning(f"⚠️ {symbol}: {limit_msg}")
                return
        except Exception as e:
            logger.debug(f"Daily trade limit check failed: {e}")
        
        # 1. Get current position
        position = await self.exchange_client.get_position(symbol)
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

        # 🎯 트레일링 익절 체크 (포지션이 있을 때만)
        try:
            current_amt = float(position.get("position_amt", 0))
            if current_amt != 0:
                current_price = float(data.get("close", 0))
                await self._check_and_update_trailing_tp(symbol, current_price)
        except Exception as e:
            logger.error(f"트레일링 익절 체크 실패 {symbol}: {e}")
        
        # 🎯 SMC (Smart Money Concept) 전략 체크
        if self.strategy_config.use_smc:
            try:
                smc_signal = await self._check_smc_strategy(symbol, position)
                if smc_signal and smc_signal.get('action') != 0:
                    logger.info(f"🎯 SMC 신호 발견: {smc_signal}")
                    # SMC 신호를 바로 실행
                    await self._execute_smc_order(symbol, smc_signal, position)
                    return  # SMC 신호 처리 후 기존 로직 스킵
            except Exception as e:
                logger.error(f"SMC 전략 실행 실패 {symbol}: {e}")
        
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
        df = await self.exchange_client.get_klines(symbol, interval=trading_interval, limit=300)
        
        # 🔧 Validate data
        if df is None or len(df) < 50:
            logger.warning(f"⚠️ Insufficient data for {symbol}: {len(df) if df is not None else 0} candles")
            return
        from ai.features import add_technical_indicators
        df = add_technical_indicators(df)
        
        # 2. Fetch 1M Data (For Spike Detection)
        # We need recent 1m candles to detect sudden moves
        df_1m_raw = await self.exchange_client.get_klines(symbol, interval='1m', limit=30)
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
        
        # 4. AI Prediction (Hybrid AI: PPO + LSTM 결합)
        # 🔧 Now using HybridAI with PPO + LSTM synergy
        if self.hybrid_ai and (self.hybrid_ai.ppo_agent or self.hybrid_ai.lstm_predictor):
            ai_action, ai_confidence = await self.hybrid_ai.predict(market_state)
        else:
            ai_action, ai_confidence = self.agent.live_predict(market_state)
            
        ai_action_name = ["HOLD", "LONG", "SHORT", "CLOSE"][ai_action]
        logger.info(f"🤖 AI Prediction (Hybrid): {ai_action_name} (Confidence: {ai_confidence:.2%})")
        
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
        ai_opposes = False
        ai_agrees = False

        if tech_signal:
             # Rule-based Signal Exists
             rule_action_id = 1 if tech_signal['action'] == "LONG" else 2
             
             # 🔧 ENHANCED AI FILTER LOGIC (Confidence-based)
             ai_opposes = (rule_action_id == 1 and ai_action == 2) or (rule_action_id == 2 and ai_action == 1)
             ai_agrees = (rule_action_id == ai_action)
             
             # 🔧 ENHANCED: Weighted Decision System (Optimized)
             # - 신호 강도 1~2: AI가 반대하면 차단
             # - 신호 강도 3: AI 신뢰도 60% 이상이고 반대하면 차단 (50% → 60%)
             # - 신호 강도 4: AI 신뢰도 75% 이상이고 반대하면 차단 (70% → 75%)
             # - 신호 강도 5: 항상 진입 (매우 강한 신호)
             
             signal_strength = tech_signal.get('strength', 1)
             
             if signal_strength >= 5:
                 # Very strong signal - always proceed
                 final_action = rule_action_id
                 reason = f"Rule_{tech_signal.get('reason', 'Signal')}"
                 logger.info(
                     f"✅ Very Strong Signal (5+), AI filter bypassed | "
                     f"AI was: {ai_action_name} ({ai_confidence:.1%})"
                 )
                 
             elif ai_opposes:
                 # AI opposes the signal
                 if signal_strength <= 2:
                     # Weak signal + AI opposition = BLOCK
                     logger.warning(
                         f"🚫 AI Blocked (Weak Signal): Rule={tech_signal['action']}, "
                         f"AI={ai_action_name} ({ai_confidence:.1%})"
                     )
                     final_action = 0
                     reason = "AI_BLOCKED_WEAK"
                 elif signal_strength == 3 and ai_confidence >= 0.6:  # 🔧 50% → 60%
                     # Medium signal + confident AI opposition = BLOCK
                     logger.warning(
                         f"🚫 AI Blocked (Medium Signal): Rule={tech_signal['action']}, "
                         f"AI={ai_action_name} ({ai_confidence:.1%})"
                     )
                     final_action = 0
                     reason = "AI_BLOCKED_MEDIUM"
                 elif signal_strength == 4 and ai_confidence >= 0.75:  # 🔧 70% → 75%
                     # Strong signal + very confident AI opposition = BLOCK
                     logger.warning(
                         f"🚫 AI Blocked (Strong Signal): Rule={tech_signal['action']}, "
                         f"AI={ai_action_name} ({ai_confidence:.1%})"
                     )
                     final_action = 0
                     reason = "AI_BLOCKED_STRONG"
                 else:
                     # Signal strong enough, proceed despite AI
                     final_action = rule_action_id
                     reason = f"Rule_{tech_signal.get('reason', 'Signal')}"
                     logger.info(
                         f"⚠️ Proceeding despite AI opposition | "
                         f"Signal:{signal_strength}, AI:{ai_action_name}({ai_confidence:.1%})"
                     )
             
             elif ai_agrees and ai_confidence >= 0.75:  # 🔧 60% → 75% (high confidence boost)
                 # AI agrees with high confidence - boost confidence
                 final_action = rule_action_id
                 reason = f"Rule+AI_HighConf_{tech_signal.get('reason', 'Signal')}"
                 logger.info(f"✅ AI High Confidence Agreement! ({ai_confidence:.1%})")
             
             elif ai_agrees and ai_confidence >= 0.6:  # Medium confidence agreement
                 # AI agrees with medium confidence
                 final_action = rule_action_id
                 reason = f"Rule+AI_{tech_signal.get('reason', 'Signal')}"
                 logger.info(f"✅ AI Agreement (Confidence: {ai_confidence:.1%})")
             
             else:
                 # Normal case - follow rule
                 final_action = rule_action_id
                 reason = f"Rule_{tech_signal.get('reason', 'Signal')}"
                 
                 # --- LEVERAGE LOGIC (Enhanced with Regime) ---
                 if self.strategy_config.leverage_mode == "MANUAL":
                     leverage = self.strategy_config.manual_leverage
                 else:
                     base_leverage = tech_signal.get('leverage', 5)
                     is_core = symbol in self.risk_config.core_coins
                     
                     # 🆕 잔고 기반 동적 레버리지 (AI + 변동성 + 신호 강도 종합)
                     try:
                         account = await self.exchange_client.get_account_info()
                         current_balance = account['balance']
                         
                         # 시장 변동성 계산 (간단히 ATR 비율 사용)
                         market_volatility = market_state.get('atr', 0.02) / float(data.get('close', 1))
                         
                         # AI 동적 레버리지 계산
                         leverage = self.balance_strategy.calculate_dynamic_leverage(
                             balance=current_balance,
                             ai_confidence=ai_confidence,
                             signal_strength=signal_strength,
                             market_volatility=market_volatility,
                             is_core=is_core
                         )
                         
                         logger.info(
                             f"🎲 Dynamic Leverage: {leverage}x "
                             f"(Balance: {current_balance:.0f} USDT, "
                             f"AI Conf: {ai_confidence:.1%}, "
                             f"Signal: {signal_strength}/5, "
                             f"Vol: {market_volatility:.2%})"
                         )
                     except Exception as e:
                         logger.warning(f"Dynamic leverage calculation failed: {e}, using fallback")
                         # Fallback: 기존 로직
                         leverage = self.regime_detector.adjust_leverage(base_leverage, current_regime, symbol)
                         if is_core:
                             if ai_agrees and ai_confidence >= 0.90:
                                 leverage = min(20, int(leverage * 1.5))
                             elif ai_agrees and ai_confidence >= 0.80:
                                 leverage = min(15, int(leverage * 1.2))
                         else:
                             leverage = min(5, leverage)
                 # ----------------------
                 
                 reason = f"Rule_{tech_signal.get('reason', 'Signal')}"
                 
                 # Apply Leverage (only if no position and different from current)
                 try:
                     current_leverage = int(position.get('leverage', 5))
                     position_size = abs(float(position.get('position_amt', 0)))
                     
                     if current_leverage != leverage and position_size == 0:
                         logger.info(f"⚙️ Applying leverage for {symbol}: {current_leverage}x -> {leverage}x ({self.strategy_config.leverage_mode} mode)")
                         await self.exchange_client.change_leverage(symbol, leverage)
                     elif current_leverage != leverage and position_size > 0:
                         logger.debug(f"Position active for {symbol}, using current leverage {current_leverage}x (Wanted: {leverage}x)")
                         leverage = current_leverage # Cannot change with position
                 except Exception as e:
                     logger.warning(f"Failed to sync leverage for {symbol}: {e}")
                     leverage = int(position.get('leverage', 5))


        else:
            # No Rule Signal
            # --- AI-FIRST ENTRY LOGIC (Enhanced with Regime) ---
            # If no technical signal, but AI has strong conviction AND regime allows, allow entry.
            ai_first_allowed = regime_params.get('allow_ai_first', False)
            
            if ai_action in [1, 2] and ai_first_allowed:
                 final_action = ai_action
                 # Use regime-adjusted leverage for AI-first trades
                 base_leverage = 5
                 leverage = self.regime_detector.adjust_leverage(base_leverage, current_regime, symbol)
                 reason = f"AI_First_{current_regime}"
                 logger.info(f"AI-Initiated Trade: {ai_action_name} | Regime: {current_regime} | Lev: {leverage}x | Symbol: {symbol}")
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
        
        # 🆕 AI Filter Summary Log
        ai_impact = "NEUTRAL"
        if reason.startswith("AI_BLOCKED"):
            ai_impact = "BLOCKED"
        elif "Rule+AI_HighConf" in reason:
            ai_impact = "HIGH_BOOST"
        elif "Rule+AI" in reason:
            ai_impact = "BOOST"
        elif ai_opposes and final_action != 0:
            ai_impact = "OPPOSED_IGNORED"
        
        logger.info(
            f"🧠 AI Filter: Tech={tech_signal['action'] if tech_signal else 'None'}(S:{signal_strength}), "
            f"AI={ai_action_name}({ai_confidence:.1%}), Impact={ai_impact}"
        )
        logger.info(
            f"🎯 DECISION {symbol} - AI: {ai_action_name} | Rule: {tech_signal['action'] if tech_signal else 'None'} -> "
            f"Final: {final_action_str} ({reason})"
        )
        
        # 신호 강도 추출
        signal_strength = tech_signal.get('strength', 0) if tech_signal else 0
        
        # 5. Execute Order (Main)
        await self._execute_order(
            symbol=symbol,
            action=final_action,
            position=position,
            price=float(latest['close']),
            atr=float(market_state.get('atr', 0)),
            reason=reason,
            leverage=int(leverage),
            market_state=market_state,
            signal_strength=signal_strength
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
        signal_strength: int = 0,
    ):
        """Execute order based on action"""
        current_amt = position['position_amt']
        
        # 🔧 STEP 1: Check Total Position Exposure (NEW!)
        if action in [1, 2] and current_amt == 0:  # New position entry
            try:
                account = await self.exchange_client.get_account_info()
                current_balance = account['balance']
                
                # Calculate current total exposure from all positions
                positions = await self.exchange_client.get_all_positions()
                total_notional = 0.0
                active_positions = 0
                long_positions = 0
                short_positions = 0
                
                for pos in positions:
                    pos_amt = float(pos.get('position_amt', 0))
                    if abs(pos_amt) > 0:
                        entry_price = float(pos.get('entry_price', 0))
                        notional = abs(pos_amt * entry_price)
                        total_notional += notional
                        active_positions += 1
                        
                        if pos_amt > 0:
                            long_positions += 1
                        else:
                            short_positions += 1
                
                current_exposure_pct = total_notional / current_balance if current_balance > 0 else 0
                
                # 🔧 CHECK 1: Total Exposure Limit
                max_exposure = self.risk_config.max_total_exposure
                if current_exposure_pct >= max_exposure:
                    logger.warning(
                        f"🚫 Total Exposure Limit Reached! "
                        f"Current: {current_exposure_pct*100:.1f}% >= Max: {max_exposure*100:.1f}% "
                        f"({active_positions} active positions, ${total_notional:.0f})"
                    )
                    return
                
                # 🔧 CHECK 2: Directional Concentration (LONG/SHORT balance)
                total_directional = long_positions + short_positions
                if total_directional > 0:
                    long_ratio = long_positions / total_directional
                    short_ratio = short_positions / total_directional
                    
                    # Block if concentration > 75% (allow max 75:25 imbalance)
                    if action == 1 and long_ratio > 0.75:  # Trying to open LONG
                        logger.warning(
                            f"🚫 LONG Concentration Too High! "
                            f"L/S Ratio: {long_positions}/{short_positions} ({long_ratio*100:.0f}%/{short_ratio*100:.0f}%) "
                            f"- Require stronger signal or wait for rebalance"
                        )
                        # Allow only if signal strength >= 5 (extremely strong)
                        if signal_strength < 5:
                            return
                        else:
                            logger.info("✅ Extremely strong signal (5+), allowing despite concentration")
                    
                    elif action == 2 and short_ratio > 0.75:  # Trying to open SHORT
                        logger.warning(
                            f"🚫 SHORT Concentration Too High! "
                            f"L/S Ratio: {long_positions}/{short_positions} ({long_ratio*100:.0f}%/{short_ratio*100:.0f}%) "
                            f"- Require stronger signal or wait for rebalance"
                        )
                        if signal_strength < 5:
                            return
                        else:
                            logger.info("✅ Extremely strong signal (5+), allowing despite concentration")
                
                # 🔧 CHECK 3: Portfolio Diversification (상관관계) 🆕
                if len(positions) >= 2:  # 2개 이상 포지션 있을 때만
                    try:
                        diversification = await self.portfolio_manager.check_diversification(
                            symbol, 
                            "LONG" if action == 1 else "SHORT",
                            [p for p in positions if abs(float(p.get('position_amt', 0))) > 0]
                        )
                        
                        if not diversification['is_diversified']:
                            logger.warning(
                                f"⚠️ Diversification Warning: {diversification['recommendation']}"
                            )
                            # 신호 강도 5 미만이면 차단
                            if signal_strength < 5:
                                logger.warning(f"🚫 Blocked due to high correlation")
                                return
                            else:
                                logger.info("✅ Extremely strong signal, allowing despite correlation")
                    except Exception as e:
                        logger.error(f"Diversification check failed: {e}")
                
                logger.info(
                    f"📊 Exposure Check: {current_exposure_pct*100:.1f}%/{max_exposure*100:.1f}% | "
                    f"Positions: {active_positions} (L:{long_positions} S:{short_positions})"
                )
                
            except Exception as e:
                logger.error(f"Exposure check failed: {e}, proceeding with caution")
        # ----------------------------------------
        
        async def _round_quantity(sym: str, qty: float):
            try:
                # 1. Fetch exchange info for precision
                info = await self.exchange_client.get_exchange_info()
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

        # Quantity logic - 🔧 ENHANCED: AI Adaptive position sizing
        # 1. Calculate Base Target Notional Value
        try:
            account = await self.exchange_client.get_account_info()
            current_balance = account['balance']
        except:
            current_balance = 5000.0  # Fallback
        
        if self.risk_config.position_mode == "ADAPTIVE":
            # 🆕 잔고 기반 동적 포지션 사이징 (AI 확신도 + 최근 성과 반영)
            try:
                # 코어코인 여부 확인
                is_core = symbol in self.risk_config.core_coins
                
                # AI 확신도 가져오기
                ai_conf = market_state.get('ai_confidence', 0.7) if market_state else 0.7
                
                # 🆕 Balance-Based Dynamic Position Sizing
                is_btc_only = coin_selector.config.get('mode') == 'BTC_ONLY'
                base_notional = self.balance_strategy.calculate_dynamic_position_size(
                    balance=current_balance,
                    ai_confidence=ai_conf,
                    is_core=is_core,
                    is_btc_only=is_btc_only
                )
                
                # 티어 정보 로깅
                tier_info = self.balance_strategy.get_current_tier(current_balance)
                mode_str = "BTC_ONLY" if is_btc_only else "HYBRID"
                logger.info(
                    f"💰 Dynamic Sizing [{tier_info['tier_name']} Tier | {mode_str}]: {symbol} = "
                    f"{base_notional:.0f} USDT "
                    f"(Balance: {current_balance:.0f}, AI Conf: {ai_conf:.1%}, "
                    f"Recent Winrate: {self.balance_strategy.get_recent_winrate():.1%}"
                )
            except Exception as e:
                logger.warning(f"Dynamic sizing failed: {e}, using fallback")
                # Fallback: 기존 로직
                is_btc_only = coin_selector.config.get('mode') == 'BTC_ONLY'
                base_notional = self.balance_strategy.calculate_dynamic_position_size(
                    balance=current_balance, 
                    ai_confidence=ai_conf, 
                    is_core=is_core,
                    is_btc_only=is_btc_only
                )
                
        elif self.risk_config.position_mode == "RATIO":
            # RATIO mode: 잔고의 고정 %
            base_notional = current_balance * self.risk_config.position_ratio
            logger.info(f"💰 Ratio Mode: {current_balance:.0f} × {self.risk_config.position_ratio*100:.1f}% = {base_notional:.0f} USDT")
            
        else:
            # FIXED mode: 고정 금액
            base_notional = 150.0
            logger.info(f"💰 Fixed Mode: {base_notional:.0f} USDT per trade")

        # 2. 🔧 Dynamic Adjustment: Signal Strength × Volatility
        # - 강한 신호 (4~5점): +30~50%
        # - 중간 신호 (2~3점): 기본
        # - 약한 신호 (1점): -30%
        signal_multiplier = 1.0
        if signal_strength >= 5:
            signal_multiplier = 1.5  # +50%
        elif signal_strength == 4:
            signal_multiplier = 1.3  # +30%
        elif signal_strength <= 1:
            signal_multiplier = 0.7  # -30%
        
        # 3. 🔧 Volatility Adjustment: 고변동성 코인 포지션 축소
        volatility_multiplier = 1.0
        if atr > 0 and market_state:
            atr_pct = (atr / price) * 100  # ATR을 %로 변환
            if atr_pct > 5.0:  # 매우 높은 변동성 (5% 이상)
                volatility_multiplier = 0.6  # -40%
                logger.info(f"🔻 High Volatility: ATR {atr_pct:.2f}%, reducing position by 40%")
            elif atr_pct > 3.0:  # 높은 변동성 (3~5%)
                volatility_multiplier = 0.8  # -20%
                logger.info(f"⚠️ Medium Volatility: ATR {atr_pct:.2f}%, reducing position by 20%")
        
        # 🆕 4. VIX Adjustment: 시장 전체 변동성 고려
        vix_multiplier = 1.0
        try:
            vix_score = await self.crypto_vix.calculate_vix()
            vix_adjustment = self.crypto_vix.get_risk_adjustment(vix_score)
            vix_multiplier = vix_adjustment['position_size_multiplier']
            
            if vix_multiplier != 1.0:
                logger.info(
                    f"📊 VIX Adjustment: Score={vix_score:.1f}, "
                    f"Regime={vix_adjustment['regime']}, "
                    f"Multiplier={vix_multiplier:.2f}"
                )
        except Exception as e:
            logger.debug(f"VIX adjustment skipped: {e}")
        
        # 🆕 5. Final calculation (with VIX)
        target_notional = base_notional * signal_multiplier * volatility_multiplier * vix_multiplier
        
        # 5. Ensure min notional > 100 USDT (Binance Testnet Limit)
        safe_notional = max(target_notional, 120.0) 
        
        min_qty = safe_notional / price
        quantity = max(0.002, min_qty) # Ensure at least 0.002 BTC
        quantity = round(quantity, 3) # Specific for BTC (3 decimal places)
        
        logger.info(
            f"📊 Position Sizing: Base={base_notional:.0f}, "
            f"Signal×{signal_multiplier:.1f}, Vol×{volatility_multiplier:.1f}, "
            f"VIX×{vix_multiplier:.1f} → Final={safe_notional:.0f} USDT"
        )

        quantity = await _round_quantity(symbol, quantity)
            
        # 🔧 Check duplicate trade prevention (15 min cooldown)
        MIN_RETRADE_MINUTES = 15
        last_trade_ts = self.last_trade_time_per_symbol.get(symbol, 0)
        time_since_last = (time.time() - last_trade_ts) / 60.0  # minutes
        
        if action in [1, 2] and last_trade_ts > 0 and time_since_last < MIN_RETRADE_MINUTES:
            logger.warning(
                f"⏸️ Duplicate Trade Prevention: {symbol} last traded {time_since_last:.1f}m ago "
                f"(need {MIN_RETRADE_MINUTES}m cooldown)"
            )
            return
        
        try:
            if action == 1: # LONG
                if current_amt <= 0: # If short or flat
                    if current_amt < 0: # Close short first (FLIP)
                        # 🎯 FLIP 제한 체크
                        can_flip = await self._can_flip_position(symbol, price, signal_strength)
                        if not can_flip:
                            logger.warning(f"⚠️ FLIP 제한: {symbol} SHORT→LONG 전환 불가 (최소 보유 시간 또는 신호 강도 부족)")
                            return
                        
                        close_order = await self.exchange_client.place_market_order(symbol, "BUY", abs(current_amt), reduce_only=True)
                        await self._handle_close_notification(
                             symbol=symbol,
                             position=position,
                             close_order=close_order,
                             fallback_price=price,
                             reason=f"FLIP_TO_LONG|{reason}".strip("|"),
                         )
                    # Open long - 🆕 Using SlippageManager
                    order = await self.slippage_manager.smart_order(symbol, "BUY", quantity)
                    logger.info("Executed LONG with slippage control")
                    # 🔧 Record trade time for duplicate prevention
                    self.last_trade_time_per_symbol[symbol] = time.time()
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
                    if current_amt > 0: # Close long first (FLIP)
                        # 🎯 FLIP 제한 체크
                        can_flip = await self._can_flip_position(symbol, price, signal_strength)
                        if not can_flip:
                            logger.warning(f"⚠️ FLIP 제한: {symbol} LONG→SHORT 전환 불가 (최소 보유 시간 또는 신호 강도 부족)")
                            return
                        
                        close_order = await self.exchange_client.place_market_order(symbol, "SELL", abs(current_amt), reduce_only=True)
                        await self._handle_close_notification(
                             symbol=symbol,
                             position=position,
                             close_order=close_order,
                             fallback_price=price,
                             reason=f"FLIP_TO_SHORT|{reason}".strip("|"),
                         )
                    # Open short - 🆕 Using SlippageManager
                    order = await self.slippage_manager.smart_order(symbol, "SELL", quantity)
                    logger.info("Executed SHORT with slippage control")
                    # 🔧 Record trade time for duplicate prevention
                    self.last_trade_time_per_symbol[symbol] = time.time()
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
                    order = await self.exchange_client.place_market_order(symbol, side, abs(current_amt), reduce_only=True)
                    logger.info("Closed Position")
                    await self._broadcast_trade("CLOSE", symbol, abs(current_amt), order)
                    await self._handle_close_notification(
                        symbol=symbol,
                        position=position,
                        close_order=order,
                        fallback_price=price,
                        reason=reason,
                    )
                    await self._clear_state(symbol)
                    
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
    
    async def _check_smc_strategy(self, symbol: str, position: Dict) -> Optional[Dict]:
        """
        SMC (Smart Money Concept) 전략 체크
        
        Returns:
            {
                'action': int,  # 0=HOLD, 1=LONG, 2=SHORT, 3=CLOSE
                'entry_price': float,
                'stop_loss': float,
                'take_profit': float,
                'confidence': float,
                'reason': str
            } or None
        """
        try:
            # 1. 고TF 데이터 (1h 또는 4h)
            high_tf = '1h' if self.strategy_config.mode == 'SCALP' else '4h'
            df_high = await self.exchange_client.get_klines(symbol, interval=high_tf, limit=300)
            if df_high is None or len(df_high) < 100:
                logger.warning(f"SMC: 고TF 데이터 부족 ({high_tf})")
                return None
            
            from ai.features import add_technical_indicators
            df_high = add_technical_indicators(df_high)
            
            # 2. 하위TF 데이터 (15m 또는 5m)
            low_tf = '15m' if self.strategy_config.mode == 'SCALP' else '30m'
            df_low = await self.exchange_client.get_klines(symbol, interval=low_tf, limit=200)
            if df_low is None or len(df_low) < 50:
                logger.warning(f"SMC: 하위TF 데이터 부족 ({low_tf})")
                return None
            
            df_low = add_technical_indicators(df_low)
            
            # 3. SMC 분석
            smc_result = self.smc_analyzer.analyze(df_high, df_low)
            
            # 4. 진입 신호 확인
            entry_signal = smc_result.get('entry_signal')
            if not entry_signal:
                return None
            
            # 5. 포지션 상태 확인
            current_amt = float(position.get('position_amt', 0))
            
            # 이미 같은 방향 포지션이 있으면 스킵
            if entry_signal['action'] == 1 and current_amt > 0:
                logger.debug(f"SMC: 이미 LONG 포지션 보유 중")
                return None
            elif entry_signal['action'] == 2 and current_amt < 0:
                logger.debug(f"SMC: 이미 SHORT 포지션 보유 중")
                return None
            
            # 6. 시장 구조와 일치하는지 확인
            market_structure = smc_result.get('market_structure', {})
            trend = market_structure.get('trend', 'UNKNOWN')
            
            # LONG 신호는 UP 트렌드에서만, SHORT 신호는 DOWN 트렌드에서만
            if entry_signal['action'] == 1 and trend != 'UP':
                logger.warning(f"SMC: LONG 신호이지만 트렌드가 {trend}")
                return None
            elif entry_signal['action'] == 2 and trend != 'DOWN':
                logger.warning(f"SMC: SHORT 신호이지만 트렌드가 {trend}")
                return None
            
            # 7. 신뢰도 체크
            if entry_signal['confidence'] < 0.6:
                logger.warning(f"SMC: 신뢰도 낮음 ({entry_signal['confidence']:.2f})")
                return None
            
            logger.info(
                f"✅ SMC 신호 발견: {['HOLD', 'LONG', 'SHORT'][entry_signal['action']]} | "
                f"신뢰도: {entry_signal['confidence']:.2f} | "
                f"트렌드: {trend} | "
                f"사유: {entry_signal['reason']}"
            )
            
            return entry_signal
            
        except Exception as e:
            logger.error(f"SMC 전략 체크 실패: {e}")
            return None
    
    async def _execute_smc_order(self, symbol: str, smc_signal: Dict, position: Dict):
        """SMC 신호 기반 주문 실행"""
        try:
            action = smc_signal['action']
            entry_price = smc_signal['entry_price']
            stop_loss = smc_signal['stop_loss']
            take_profit = smc_signal['take_profit']
            reason = smc_signal['reason']
            
            current_amt = float(position.get('position_amt', 0))
            
            # 수량 계산
            async def _round_quantity(sym: str, qty: float):
                try:
                    info = await self.exchange_client.get_exchange_info()
                    if not info or 'symbols' not in info:
                        return round(qty, 3)
                    
                    s_info = next((s for s in info['symbols'] if s['symbol'] == sym), None)
                    if not s_info:
                        return round(qty, 3)
                    
                    precision = int(s_info.get('quantityPrecision', 3))
                    
                    import math
                    factor = 10 ** precision
                    return math.floor(qty * factor) / factor
                except:
                    return round(qty, 3)
            
            # 목표 금액 - 🔧 Use same adaptive logic as main trading
            try:
                account = await self.exchange_client.get_account_info()
                current_balance = account['balance']
            except:
                current_balance = 5000.0
            
            if self.risk_config.position_mode == "ADAPTIVE":
                try:
                    # 코어코인 여부 확인
                    is_core = symbol in self.risk_config.core_coins
                    if is_core:
                        target_notional = current_balance * self.risk_config.core_coin_ratio
                    else:
                        target_notional = current_balance * self.risk_config.alt_coin_ratio
                except:
                    target_notional = current_balance * 0.03
            elif self.risk_config.position_mode == "RATIO":
                target_notional = current_balance * self.risk_config.position_ratio
            else:
                target_notional = 150.0
            
            safe_notional = max(target_notional, 120.0)
            min_qty = safe_notional / entry_price
            quantity = max(0.002, min_qty)
            quantity = await _round_quantity(symbol, quantity)
            
            # 레버리지 설정
            leverage = self.strategy_config.manual_leverage if self.strategy_config.leverage_mode == "MANUAL" else 5
            
            try:
                current_leverage = position.get('leverage', 5)
                position_size = abs(float(position.get('position_amt', 0)))
                
                if current_leverage != leverage and position_size == 0:
                    result = await self.exchange_client.change_leverage(symbol, leverage)
                    if result is not None:
                        logger.info(f"✓ 레버리지 변경: {current_leverage} -> {leverage}")
                    else:
                        leverage = current_leverage
                elif current_leverage != leverage and position_size > 0:
                    leverage = current_leverage
            except Exception as e:
                logger.debug(f"레버리지 변경 오류 ({e}), 기존 레버리지 사용: {leverage}")
            
            # 주문 실행
            if action == 1:  # LONG
                if current_amt < 0:  # SHORT 포지션 청산
                    close_order = await self.exchange_client.place_market_order(symbol, "BUY", abs(current_amt), reduce_only=True)
                    await self._handle_close_notification(
                        symbol=symbol,
                        position=position,
                        close_order=close_order,
                        fallback_price=entry_price,
                        reason=f"SMC_FLIP_TO_LONG",
                    )
                
                # LONG 진입
                order = await self.exchange_client.place_market_order(symbol, "BUY", quantity)
                logger.info(f"🎯 SMC LONG 진입: {symbol} @ {entry_price:.2f}")
                await self._broadcast_trade("LONG", symbol, quantity, order)
                
                # TP/SL 설정 (SMC 신호 사용)
                try:
                    res = await self.exchange_client.place_bracket_orders(
                        symbol=symbol,
                        position_side="LONG",
                        quantity=float(quantity),
                        stop_loss_price=stop_loss,
                        take_profit_price=take_profit,
                    )
                    
                    actual_entry = float(order.get("avgPrice", 0) or order.get("price", 0) or entry_price)
                    
                    self.brackets[symbol] = {
                        "symbol": symbol,
                        "side": "LONG",
                        "qty": float(quantity),
                        "leverage": int(leverage),
                        "entry_price": actual_entry,
                        "tp": float(take_profit),
                        "sl": float(stop_loss),
                        "tp_order_id": (res.get("tp") or {}).get("orderId") if res.get("tp") else None,
                        "sl_order_id": (res.get("sl") or {}).get("orderId") if res.get("sl") else None,
                        "entry_ts": time.time(),
                        "entry_reason": reason,
                        "high_water_mark": actual_entry,
                        "low_water_mark": None,
                        "trailing_active": False,
                        "initial_tp": float(take_profit),
                        "initial_sl": float(stop_loss),
                    }
                    
                    logger.info(f"✅ SMC LONG 브래킷 설정: TP={take_profit:.2f}, SL={stop_loss:.2f}")
                    await self._save_state(symbol)
                except Exception as e:
                    logger.error(f"SMC 브래킷 주문 실패: {e}")
            
            elif action == 2:  # SHORT
                if current_amt > 0:  # LONG 포지션 청산
                    close_order = await self.exchange_client.place_market_order(symbol, "SELL", abs(current_amt), reduce_only=True)
                    await self._handle_close_notification(
                        symbol=symbol,
                        position=position,
                        close_order=close_order,
                        fallback_price=entry_price,
                        reason=f"SMC_FLIP_TO_SHORT",
                    )
                
                # SHORT 진입
                order = await self.exchange_client.place_market_order(symbol, "SELL", quantity)
                logger.info(f"🎯 SMC SHORT 진입: {symbol} @ {entry_price:.2f}")
                await self._broadcast_trade("SHORT", symbol, quantity, order)
                
                # TP/SL 설정
                try:
                    res = await self.exchange_client.place_bracket_orders(
                        symbol=symbol,
                        position_side="SHORT",
                        quantity=float(quantity),
                        stop_loss_price=stop_loss,
                        take_profit_price=take_profit,
                    )
                    
                    actual_entry = float(order.get("avgPrice", 0) or order.get("price", 0) or entry_price)
                    
                    self.brackets[symbol] = {
                        "symbol": symbol,
                        "side": "SHORT",
                        "qty": float(quantity),
                        "leverage": int(leverage),
                        "entry_price": actual_entry,
                        "tp": float(take_profit),
                        "sl": float(stop_loss),
                        "tp_order_id": (res.get("tp") or {}).get("orderId") if res.get("tp") else None,
                        "sl_order_id": (res.get("sl") or {}).get("orderId") if res.get("sl") else None,
                        "entry_ts": time.time(),
                        "entry_reason": reason,
                        "high_water_mark": None,
                        "low_water_mark": actual_entry,
                        "trailing_active": False,
                        "initial_tp": float(take_profit),
                        "initial_sl": float(stop_loss),
                    }
                    
                    logger.info(f"✅ SMC SHORT 브래킷 설정: TP={take_profit:.2f}, SL={stop_loss:.2f}")
                    await self._save_state(symbol)
                except Exception as e:
                    logger.error(f"SMC 브래킷 주문 실패: {e}")
            
        except Exception as e:
            logger.error(f"SMC 주문 실행 실패: {e}")
            await self._notify_error(f"SMC 주문 실행 실패: {e}", context={"symbol": symbol})
            
    async def _save_state(self, symbol: str):
        """Save bracket state to DB"""
        try:
            from app.database import SessionLocal
            from app.models import TradeState
            import json
            
            bracket = self.brackets.get(symbol)
            if not bracket:
                return

            data_str = json.dumps(bracket)
            
            async with SessionLocal() as db:
                # Upsert
                existing = await db.get(TradeState, symbol)
                if existing:
                    existing.data = data_str
                    existing.updated_at = datetime.utcnow()
                else:
                    new_state = TradeState(symbol=symbol, data=data_str)
                    db.add(new_state)
                await db.commit()
                
        except Exception as e:
            logger.error(f"Failed to save state for {symbol}: {e}")

    async def _clear_state(self, symbol: str):
        """Remove state from DB"""
        try:
            from app.database import SessionLocal
            from app.models import TradeState
            
            if symbol in self.brackets:
                del self.brackets[symbol]
                
            async with SessionLocal() as db:
                existing = await db.get(TradeState, symbol)
                if existing:
                    await db.delete(existing)
                    await db.commit()
                    
        except Exception as e:
            logger.error(f"Failed to clear state for {symbol}: {e}")

    async def _load_state(self):
        """Load active brackets from DB"""
        try:
            from app.database import SessionLocal
            from app.models import TradeState
            import json
            from sqlalchemy import select
            
            async with SessionLocal() as db:
                result = await db.execute(select(TradeState))
                states = result.scalars().all()
                
                count = 0
                for s in states:
                    try:
                        self.brackets[s.symbol] = json.loads(s.data)
                        count += 1
                        # Restore open timestamp if not present
                        if s.symbol not in self.position_open_ts:
                            self.position_open_ts[s.symbol] = self.brackets[s.symbol].get('entry_ts', time.time())
                    except:
                        pass
                
                if count > 0:
                    logger.info(f"🔄 Restored {count} active bracket orders from DB")
                    
        except Exception as e:
            logger.error(f"Failed to load state: {e}")

    def _fmt_usdt(self, x: float) -> str:
        try:
            if x < 0.1: return f"{x:.5f}" # Very cheap
            if x < 1: return f"{x:.4f}" # Cheap
            if x < 10: return f"{x:.3f}" # Mid
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
            # 🔧 모드 정보 전달
            sltp = self.sl_tp_ai.get_sl_tp_for_position(
                position={"entry_price": entry_price, "position_amt": pos_amt, "unrealized_pnl": 0.0},
                current_market_data={
                    "close": entry_price,
                    "atr": float(atr),
                    "rsi": float(market_state.get("rsi", 50.0)),
                    "macd": float(market_state.get("macd", 0.0)),
                },
                trading_mode=self.strategy_config.mode  # 🔧 SCALP or SWING
            )
            sl_price = float(sltp.get("sl_price")) if sltp.get("sl_price") is not None else None
            tp_price = float(sltp.get("tp_price")) if sltp.get("tp_price") is not None else None
        except Exception as e:
            await self._notify_error(f"SL/TP compute failed: {e}", context={"symbol": symbol})

        # Place bracket orders (best-effort)
        try:
            res = await self.exchange_client.place_bracket_orders(
                symbol=symbol,
                position_side=side,
                quantity=float(quantity),
                stop_loss_price=sl_price,
                take_profit_price=tp_price,
            )
            tp_order_id = None
            sl_order_id = None
            if res.get("tp"):
                tp_order_id = res["tp"].get("orderId")
            if res.get("sl"):
                sl_order_id = res["sl"].get("orderId")
            
            self.brackets[symbol] = {
                "symbol": symbol,
                "side": side,
                "qty": float(quantity),
                "leverage": int(leverage),
                "entry_price": float(entry_price),
                "tp": float(tp_price) if tp_price is not None else None,
                "sl": float(sl_price) if sl_price is not None else None,
                "tp_order_id": tp_order_id,
                "sl_order_id": sl_order_id,
                "entry_ts": time.time(),
                "entry_reason": reason,
                # Trailing Take Profit fields
                "high_water_mark": float(entry_price) if side == "LONG" else None,
                "low_water_mark": float(entry_price) if side == "SHORT" else None,
                "trailing_active": False,
                "initial_tp": float(tp_price) if tp_price is not None else None,
                "initial_sl": float(sl_price) if sl_price is not None else None,
                "initial_qty": float(quantity),  # 🆕 부분 청산용
            }
            
            # 🆕 부분 청산 초기화
            self.partial_exit_manager.initialize_symbol(symbol, self.strategy_config.mode)
            
            await self._save_state(symbol)
            return entry_price, tp_price, sl_price

        except Exception as e:
            logger.error(f"Bracket order placement failed: {e}")
            await self._notify_error(f"Bracket setup failed: {e}", context={"symbol": symbol})
            return entry_price, tp_price, sl_price

    async def _can_flip_position(self, symbol: str, current_price: float, signal_strength: int) -> bool:
        """
        포지션 FLIP(방향 전환) 가능 여부 체크
        허용 조건:
        1. 최소 보유 시간 미달 (빠른 손절)
        2. 강력한 신호 (4점 이상)
        3. 손절가 도달
        """
        bracket = self.brackets.get(symbol)
        if not bracket:
            return True  # 브래킷 정보 없으면 허용 (안전)
        
        entry_ts = bracket.get("entry_ts", 0)
        if not entry_ts:
            return True
        
        # 🔧 모드별 최소 보유 시간
        mode_config = self.trailing_config.get_config_for_mode(self.strategy_config.mode)
        min_hold = mode_config['min_hold_minutes']
        
        # 최소 보유 시간 체크
        hold_minutes = (time.time() - entry_ts) / 60.0
        
        # 조건 1: 최소 보유 시간 미달 (빠른 손절)
        if hold_minutes < min_hold:
            logger.info(f"✅ FLIP 허용 (빠른 손절): {symbol} 보유시간 {hold_minutes:.1f}분 < {min_hold}분")
            return True
        
        # 조건 2: 강력한 신호 (모드별)
        min_signal = mode_config['flip_min_signal_score']
        if signal_strength >= min_signal:
            logger.info(f"✅ FLIP 허용 (강력한 신호): {symbol} 신호 강도 {signal_strength} >= {min_signal}")
            return True
        
        # 조건 3: 손절가 도달 여부 체크
        sl_price = bracket.get("sl")
        side = bracket.get("side")
        
        if sl_price and side:
            if side == "LONG" and current_price <= sl_price * 1.005:  # 0.5% 여유
                logger.info(f"✅ FLIP 허용 (손절가 도달): {symbol} LONG 현재가 {current_price:.2f} <= SL {sl_price:.2f}")
                return True
            elif side == "SHORT" and current_price >= sl_price * 0.995:  # 0.5% 여유
                logger.info(f"✅ FLIP 허용 (손절가 도달): {symbol} SHORT 현재가 {current_price:.2f} >= SL {sl_price:.2f}")
                return True
        
        # 모든 조건 미달
        logger.warning(
            f"⚠️ FLIP 거부: {symbol} "
            f"보유시간 {hold_minutes:.1f}분 >= {min_hold}분, "
            f"신호강도 {signal_strength} < {min_signal}, "
            f"손절가 미도달"
        )
        return False

    async def _check_and_update_trailing_tp(self, symbol: str, current_price: float):
        """
        트레일링 익절 체크 및 업데이트
        - 최고가/최저가 업데이트
        - 트레일링 활성화 조건 체크
        - 익절가 동적 조정
        - 🆕 부분 청산 체크
        - 🆕 Trailing SL 체크
        """
        if not self.trailing_config.enabled:
            return
        
        bracket = self.brackets.get(symbol)
        if not bracket:
            return
        
        side = bracket.get("side")
        entry_price = bracket.get("entry_price", 0)
        entry_ts = bracket.get("entry_ts", 0)
        
        if not entry_price or not entry_ts:
            return
        
        # 🔧 모드별 트레일링 설정
        mode_config = self.trailing_config.get_config_for_mode(self.strategy_config.mode)
        
        # 최소 보유 시간 체크
        hold_minutes = (time.time() - entry_ts) / 60.0
        if hold_minutes < mode_config['min_hold_minutes']:
            return
        
        # 🆕 1. 부분 청산 체크
        try:
            exit_result = await self.partial_exit_manager.check_partial_exits(
                symbol, bracket, current_price, self.exchange_client
            )
            
            if exit_result:
                logger.info(
                    f"💰 Partial Exit Complete: {symbol} {exit_result['level']} "
                    f"at +{exit_result['pnl_pct']:.2f}%"
                )
                
                # 첫 익절 후 본전 SL 설정
                if self.partial_exit_manager.should_set_breakeven(symbol):
                    await move_sl_to_breakeven(self.exchange_client, self.brackets, symbol, entry_price)
                    self.partial_exit_manager.mark_breakeven_set(symbol)
        except Exception as e:
            logger.error(f"Partial exit check failed for {symbol}: {e}")
        
        # 🆕 2. Trailing SL 체크 (수익 나고 있을 때)
        try:
            await update_trailing_stop_loss(
                self.exchange_client, self.brackets, symbol, current_price, entry_price, side, bracket
            )
        except Exception as e:
            logger.error(f"Trailing SL update failed for {symbol}: {e}")
        
        leverage = bracket.get("leverage", 1)
        
        # LONG 포지션 트레일링
        if side == "LONG":
            # 최고가 업데이트
            high_water_mark = bracket.get("high_water_mark", entry_price)
            if current_price > high_water_mark:
                high_water_mark = current_price
                bracket["high_water_mark"] = high_water_mark
                logger.debug(f"🎯 {symbol} LONG 최고가 업데이트: {high_water_mark:.2f}")
            
            # 수익률 계산 (레버리지 고려)
            profit_pct = ((current_price - entry_price) / entry_price) * 100.0 * leverage
            
            # 트레일링 활성화 조건 체크
            if not bracket.get("trailing_active") and profit_pct >= self.trailing_config.activation_pct:
                bracket["trailing_active"] = True
                logger.info(f"✨ {symbol} 트레일링 익절 활성화! 수익률: {profit_pct:.2f}% (최소: {self.trailing_config.activation_pct}%)")
            
            # 트레일링 활성화 시 익절가 동적 조정 (모드별)
            if bracket.get("trailing_active"):
                # 최고가에서 distance_pct% 하락한 가격으로 익절가 설정
                new_tp = high_water_mark * (1 - mode_config['distance_pct'] / 100.0)
                current_tp = bracket.get("tp")
                
                # 익절가가 진입가보다 높고, 기존 익절가보다 높으면 업데이트
                if new_tp > entry_price and (not current_tp or new_tp > current_tp):
                    try:
                        # 기존 익절 주문 취소
                        if bracket.get("tp_order_id"):
                            await self.exchange_client.cancel_order(symbol, bracket["tp_order_id"])
                        
                        # 새 익절 주문 생성
                        qty = bracket.get("qty", 0)
                        new_tp_order = await self.exchange_client.place_limit_order(
                            symbol=symbol,
                            side="SELL",
                            quantity=qty,
                            price=new_tp,
                            reduce_only=True
                        )
                        
                        bracket["tp"] = new_tp
                        bracket["tp_order_id"] = new_tp_order.get("orderId")
                        
                        logger.info(f"📈 {symbol} LONG 익절가 상향: {current_tp:.2f} → {new_tp:.2f} (최고가: {high_water_mark:.2f})")
                    except Exception as e:
                        logger.error(f"트레일링 익절가 업데이트 실패 {symbol}: {e}")
        
        # SHORT 포지션 트레일링
        elif side == "SHORT":
            # 최저가 업데이트
            low_water_mark = bracket.get("low_water_mark", entry_price)
            if current_price < low_water_mark:
                low_water_mark = current_price
                bracket["low_water_mark"] = low_water_mark
                logger.debug(f"🎯 {symbol} SHORT 최저가 업데이트: {low_water_mark:.2f}")
            
            # 수익률 계산 (레버리지 고려)
            profit_pct = ((entry_price - current_price) / entry_price) * 100.0 * leverage
            
            # 트레일링 활성화 조건 체크 (모드별)
            if not bracket.get("trailing_active") and profit_pct >= mode_config['activation_pct']:
                bracket["trailing_active"] = True
                logger.info(f"✨ {symbol} 트레일링 익절 활성화! 수익률: {profit_pct:.2f}% (최소: {mode_config['activation_pct']}%)")
            
            # 트레일링 활성화 시 익절가 동적 조정 (모드별)
            if bracket.get("trailing_active"):
                # 최저가에서 distance_pct% 상승한 가격으로 익절가 설정
                new_tp = low_water_mark * (1 + mode_config['distance_pct'] / 100.0)
                current_tp = bracket.get("tp")
                
                # 익절가가 진입가보다 낮고, 기존 익절가보다 낮으면 업데이트
                if new_tp < entry_price and (not current_tp or new_tp < current_tp):
                    try:
                        # 기존 익절 주문 취소
                        if bracket.get("tp_order_id"):
                            await self.exchange_client.cancel_order(symbol, bracket["tp_order_id"])
                        
                        # 새 익절 주문 생성
                        qty = bracket.get("qty", 0)
                        new_tp_order = await self.exchange_client.place_limit_order(
                            symbol=symbol,
                            side="BUY",
                            quantity=abs(qty),
                            price=new_tp,
                            reduce_only=True
                        )
                        
                        bracket["tp"] = new_tp
                        bracket["tp_order_id"] = new_tp_order.get("orderId")
                        
                        logger.info(f"📉 {symbol} SHORT 익절가 하향: {current_tp:.2f} → {new_tp:.2f} (최저가: {low_water_mark:.2f})")
                    except Exception as e:
                        logger.error(f"트레일링 익절가 업데이트 실패 {symbol}: {e}")

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
            await self.exchange_client.cancel_open_orders(symbol)
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
            
            # 🆕 거래 결과 기록 (Balance-Based Strategy)
            try:
                is_win = pnl > 0
                self.balance_strategy.add_trade_result(symbol, float(pnl), is_win)
                logger.debug(f"📊 Trade result recorded: {symbol} {'WIN' if is_win else 'LOSS'} (PnL: {pnl:+.2f})")
            except Exception as record_err:
                logger.debug(f"Failed to record trade result: {record_err}")
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
            await self.exchange_client.cancel_open_orders(symbol)
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
            account = await self.exchange_client.get_account_info()
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

    async def _performance_monitor_loop(self):
        """🆕 Performance monitoring loop (every 6 hours)"""
        try:
            while self.running:
                await asyncio.sleep(6 * 3600)  # 6시간마다
                if not self.running:
                    break
                
                # 성과 체크
                result = await self.performance_monitor.check_performance_degradation(days=7)
                
                if result['status'] in ['warning', 'critical']:
                    logger.warning(f"⚠️ Performance degradation detected: {result['status']}")
                    
                    # 재학습 필요 시
                    if result['needs_retraining']:
                        await self.performance_monitor.trigger_retraining()
                
        except asyncio.CancelledError:
            return
        except Exception as e:
            await self._notify_error(f"Performance monitor loop failed: {e}")
    
    async def _send_daily_report(self):
        if not notification_manager.enabled_channels.get("telegram", False):
            return
        try:
            account = await self.exchange_client.get_account_info()
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
