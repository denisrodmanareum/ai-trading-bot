"""
PPO (Proximal Policy Optimization) Trading Agent
"""
import os
from typing import Optional, Dict
import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import DummyVecEnv
from loguru import logger
import json
from datetime import datetime

from ai.environment import TradingEnvironment
from app.core.config import settings


from cleanup_models import cleanup_models

class TradingCallback(BaseCallback):
    """Custom callback for monitoring training progress"""
    
    def __init__(self, verbose=0, save_freq=1000, save_path='./data/models', symbol='BTCUSDT', interval='1h'):
        super().__init__(verbose)
        self.save_freq = save_freq
        self.save_path = save_path
        self.symbol = symbol
        self.interval = interval
        self.episode_rewards = []
        self.episode_lengths = []
        
        os.makedirs(save_path, exist_ok=True)
    
    def _on_step(self) -> bool:
        # ⚠️ 중간 저장 비활성화 - 최종 모델만 저장
        # if self.n_calls % self.save_freq == 0:
        #     model_path = os.path.join(
        #         self.save_path,
        #         f'ppo_{self.symbol}_{self.interval}_{self.n_calls}.zip'
        #     )
        #     self.model.save(model_path)
        #     logger.info(f"Model saved at step {self.n_calls}")
        
        return True
    
    def _on_rollout_end(self) -> None:
        """Called at the end of a rollout"""
        if len(self.model.ep_info_buffer) > 0:
            mean_reward = np.mean([ep_info["r"] for ep_info in self.model.ep_info_buffer])
            mean_length = np.mean([ep_info["l"] for ep_info in self.model.ep_info_buffer])
            
            self.episode_rewards.append(mean_reward)
            self.episode_lengths.append(mean_length)
            
            logger.info(f"Rollout: Reward={mean_reward:.2f}, Length={mean_length:.0f}")


class TradingAgent:
    """PPO-based Trading Agent"""
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        learning_rate: float = None,
        gamma: float = None,
        batch_size: int = None,
        n_epochs: int = None
    ):
        self.learning_rate = learning_rate or settings.AI_LEARNING_RATE
        self.gamma = gamma or settings.AI_GAMMA
        self.batch_size = batch_size or settings.AI_BATCH_SIZE
        self.n_epochs = n_epochs or settings.AI_UPDATE_EPOCHS
        
        self.model: Optional[PPO] = None
        self.env: Optional[TradingEnvironment] = None
        self.model_path = model_path
        
        self.training_history = {
            'episodes': [],
            'rewards': [],
            'balances': [],
            'win_rates': []
        }
    
    def create_environment(self, df, **kwargs):
        """Create trading environment"""
        self.env = TradingEnvironment(df, **kwargs)
        return self.env
    
    def build_model(self, env):
        """Build new PPO model"""
        logger.info("Building new PPO model...")
        
        self.model = PPO(
            "MlpPolicy",
            env,
            learning_rate=self.learning_rate,
            gamma=self.gamma,
            batch_size=self.batch_size,
            n_epochs=self.n_epochs,
            verbose=1,
            tensorboard_log=os.path.join(os.getcwd(), "data", "tensorboard"),
            device='cuda' if torch.cuda.is_available() else 'cpu'
        )
        
        logger.info(f"Model created on device: {self.model.device}")
        return self.model
    
    def load_model(self, path: str):
        """Load pre-trained model"""
        try:
            logger.info(f"Loading model from {path}")
            # Detect Git LFS pointer file (happens when git-lfs isn't installed or git lfs pull wasn't run)
            try:
                import os
                if os.path.exists(path) and os.path.getsize(path) < 2048:
                    with open(path, "rb") as f:
                        head = f.read(2048)
                    if b"git-lfs.github.com/spec/v1" in head:
                        raise RuntimeError(
                            "모델 파일이 Git LFS 포인터로 내려왔습니다. "
                            "다른 PC에서 아래를 실행하세요: "
                            "`git lfs install` 후 `git lfs pull`"
                        )
            except Exception as e:
                # If we raised our own error, re-raise; otherwise ignore detection issues
                if isinstance(e, RuntimeError):
                    raise
            self.model = PPO.load(path)
            self.model_path = path
            logger.info("Model loaded successfully")
            return self.model
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
        if path is None:
            # Default name if not provided (should be passed generally)
            # We add specific symbol argument in next signature update or use generic
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # This method signature didn't change in this chunk, assuming called with explicit path or default
            # But let's check `train` - it calls `save_model()` without args. 
            # We need to update `save_model` signature to take `symbol` optionally or handle it.
            # Ideally `save_model` takes `symbol` arg.
            pass

    def save_model(self, path: str = None, symbol: str = "BTCUSDT", interval: str = "1h"):
        """Save current model with symbol and interval info"""
        if self.model is None:
            logger.warning("No model to save")
            return
        
        if path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            # 새로운 파일명 형식: ppo_BTCUSDT_1m_20240124_1430.zip
            path = os.path.join(
                settings.AI_MODEL_PATH,
                f"ppo_{symbol}_{interval}_{timestamp}.zip"
            )
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.model.save(path)
        self.model_path = path
        logger.info(f"✅ Model saved to {path}")
        
        # Save training history
        history_path = path.replace('.zip', '_history.json')
        with open(history_path, 'w') as f:
            json.dump(self.training_history, f, indent=2)
            
        # 같은 symbol+interval의 이전 모델들 삭제 (최신 1개만 유지)
        try:
            import glob
            pattern = os.path.join(settings.AI_MODEL_PATH, f"ppo_{symbol}_{interval}_*.zip")
            existing_models = sorted(glob.glob(pattern), reverse=True)
            
            # 현재 저장한 모델을 제외한 나머지 삭제
            for old_model in existing_models[1:]:
                try:
                    os.remove(old_model)
                    # 히스토리 파일도 삭제
                    old_history = old_model.replace('.zip', '_history.json')
                    if os.path.exists(old_history):
                        os.remove(old_history)
                    logger.info(f"🗑️ Removed old model: {os.path.basename(old_model)}")
                except Exception as e:
                    logger.error(f"Failed to remove {old_model}: {e}")
                    
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
        
        return path
    
    def optimize(self, df, n_trials=10):
        """Run hyperparameter optimization"""
        from ai.optimization import HyperOptimizer
        
        # Save current df to csv for optimizer (simplified)
        data_path = "data/train_data_opt.csv"
        df.to_csv(data_path, index=False)
        
        optimizer = HyperOptimizer(data_path=data_path, n_trials=n_trials)
        best_params, best_value = optimizer.run_optimization()
        
        # Update agent params
        self.learning_rate = best_params['learning_rate']
        self.gamma = best_params['gamma']
        self.batch_size = best_params['batch_size']
        # n_steps and ent_coef are not stored in self currently, 
        # but we can save them for build_model
        
        # Rebuild model with best params
        self.learning_rate = best_params['learning_rate']
        self.gamma = best_params['gamma']
        self.batch_size = best_params['batch_size']
        
        training_args = {
            "n_steps": best_params['n_steps'],
            "ent_coef": best_params['ent_coef']
        }
        
        return best_params

    def train(
        self,
        df,
        total_timesteps: int = 100000,
        save_freq: int = 10000,
        symbol: str = "BTCUSDT",
        interval: str = "1h",
        **env_kwargs
    ):
        """Train the agent"""
        logger.info(f"🚀 Starting training for {symbol} ({interval})...")
        
        # Create environment
        env = self.create_environment(df, **env_kwargs)
        vec_env = DummyVecEnv([lambda: env])
        
        # Build or use existing model
        if self.model is None:
            self.build_model(vec_env)
        else:
            self.model.set_env(vec_env)
        
        # Create callback (중간 저장은 비활성화됨)
        callback = TradingCallback(
            save_freq=save_freq,
            save_path=settings.AI_MODEL_PATH,
            symbol=symbol,
            interval=interval
        )
        
        # Train
        try:
            self.model.learn(
                total_timesteps=total_timesteps,
                callback=callback,
                progress_bar=True
            )
            
            # Update training history
            self.training_history['episodes'].extend(callback.episode_rewards)
            self.training_history['rewards'].extend(callback.episode_rewards)
            
            logger.info("✅ Training completed successfully")
            
            # Save final model (최종 모델만 저장)
            final_path = self.save_model(symbol=symbol, interval=interval)
            return final_path
            
        except Exception as e:
            logger.error(f"❌ Training failed: {e}")
            raise
    
    def predict(self, observation, deterministic: bool = True):
        """Predict action for given observation"""
        if self.model is None:
            raise ValueError("Model not loaded or trained")
        
        action, _states = self.model.predict(observation, deterministic=deterministic)
        return action
    
    def backtest(self, df, **env_kwargs) -> Dict:
        """Backtest the trained model"""
        logger.info("Starting backtest...")
        
        if self.model is None:
            raise ValueError("Model not loaded or trained")
        
        # Create environment
        env = self.create_environment(df, **env_kwargs)
        
        # Run episode
        obs, _ = env.reset()
        done = False
        truncated = False
        total_reward = 0
        signal_overrides = 0
        
        while not done and not truncated:
            # stable-baselines3 may return numpy scalar/array; normalize to int
            action = int(self.predict(obs, deterministic=True))
            
            # Fallback: if the model never enters (common degenerate policy), use stochastic signal
            # as a guardrail so backtests produce meaningful trades.
            try:
                pos = int(getattr(env, "position", 0))
                stoch = env.get_stochastic_signal() if hasattr(env, "get_stochastic_signal") else {"signal": "NEUTRAL", "strength": 0}
                sig = stoch.get("signal", "NEUTRAL")
                strength = int(stoch.get("strength", 0) or 0)
                
                buy_sigs = {"BUY", "STRONG_BUY"}
                sell_sigs = {"SELL", "STRONG_SELL"}
                
                # If flat and model is HOLD/CLOSE, enter on at-least BUY/SELL strength>=2
                if pos == 0 and action in (0, 3) and strength >= 2:
                    if sig in buy_sigs:
                        action = 1
                        signal_overrides += 1
                    elif sig in sell_sigs:
                        action = 2
                        signal_overrides += 1
                
                # If in position and model keeps holding, allow a strong opposite signal to close
                if pos == 1 and action == 0 and sig == "STRONG_SELL" and strength >= 3:
                    action = 3
                    signal_overrides += 1
                elif pos == -1 and action == 0 and sig == "STRONG_BUY" and strength >= 3:
                    action = 3
                    signal_overrides += 1
            except Exception:
                pass

            obs, reward, done, truncated, info = env.step(action)
            total_reward += reward
        
        # IMPORTANT: Trades are counted on CLOSE in TradingEnvironment.
        # If the agent opens a position and never closes it before the episode ends,
        # total_trades will remain 0. To make backtest results meaningful, force-close
        # any open position at the end using the last available price.
        try:
            if getattr(env, "position", 0) != 0:
                # env.current_step is already advanced; clamp index to last candle
                last_idx = min(getattr(env, "current_step", len(env.df) - 1), len(env.df) - 1)
                last_price = float(env.df.iloc[last_idx]["close"])
                env._close_position(last_price)  # increments total_trades and updates balance
        except Exception as e:
            logger.warning(f"Backtest force-close failed: {e}")
        
        # Get performance metrics
        metrics = env.get_performance_metrics()
        metrics['total_reward'] = total_reward
        metrics["signal_overrides"] = int(signal_overrides)
        
        # Add action distribution for debugging (0=HOLD, 1=LONG, 2=SHORT, 3=CLOSE)
        try:
            from collections import Counter
            action_counts = Counter(getattr(env, "action_history", []))
            metrics["action_counts"] = {
                "HOLD": int(action_counts.get(0, 0)),
                "LONG": int(action_counts.get(1, 0)),
                "SHORT": int(action_counts.get(2, 0)),
                "CLOSE": int(action_counts.get(3, 0)),
            }
            metrics["ended_with_open_position"] = bool(getattr(env, "position", 0) != 0)
        except Exception:
            pass

        # Ensure JSON-serializable types (convert numpy scalars, etc.)
        try:
            import numpy as _np

            def _to_builtin(v):
                if isinstance(v, dict):
                    return {k: _to_builtin(x) for k, x in v.items()}
                if isinstance(v, (list, tuple)):
                    return [_to_builtin(x) for x in v]
                if isinstance(v, _np.generic):
                    return v.item()
                return v

            metrics = _to_builtin(metrics)
        except Exception:
            pass
        
        logger.info(f"Backtest completed: {metrics}")
        return metrics
    
    def live_predict(self, market_data: Dict) -> tuple[int, float]:
        """
        Predict action for live trading with confidence score
        
        Args:
            market_data: Dictionary containing current market state
            
        Returns:
            (action, confidence): action: 0=Hold, 1=Long, 2=Short, 3=Close
                                 confidence: 0.0~1.0 (AI certainty)
        """
        if self.model is None:
            raise ValueError("Model not loaded")
        
        # Convert market data to observation format
        obs = self._prepare_observation(market_data)
        
        # 🔧 Get action probabilities for confidence
        try:
            import torch
            obs_tensor = torch.FloatTensor(obs).unsqueeze(0)
            with torch.no_grad():
                action_probs = self.model.policy.get_distribution(obs_tensor).distribution.probs
                probs = action_probs.cpu().numpy()[0]
        except Exception as e:
            logger.debug(f"Could not extract probabilities: {e}")
            probs = None
        
        # Predict action
        action = self.predict(obs, deterministic=True)
        action = int(action)
        
        # 🔧 Calculate confidence (probability of selected action)
        if probs is not None and len(probs) > action:
            confidence = float(probs[action])
        else:
            confidence = 0.5  # Default: uncertain
        
        logger.debug(f"AI: Action={action}, Confidence={confidence:.2f}")
        
        return action, confidence
    
    def _prepare_observation(self, market_data: Dict) -> np.ndarray:
        """
        Prepare observation from market data
        
        Expected market_data format:
        {
            'close': float,
            'volume': float,
            'rsi': float,
            'macd': float,
            'signal': float,
            'bb_upper': float,
            'bb_lower': float,
            'atr': float,
            'position': int (-1, 0, 1),
            'position_size': float,
            'entry_price': float,
            'balance': float,
            'initial_balance': float
        }
        """
        close = market_data['close']
        
        # Calculate derived values
        # Calculate derived values
        position_ratio = market_data.get('position', 0)
        unrealized_pnl = 0.0
        entry_price = 0.0  # Initialize default
        
        if position_ratio != 0:
            entry_price = market_data.get('entry_price', close)
            position_size = market_data.get('position_size', 0)
            balance = market_data.get('balance', settings.INITIAL_BALANCE)
            
            unrealized_pnl = (close - entry_price) * position_ratio * position_size
            unrealized_pnl /= balance if balance > 0 else 1.0
        
        balance_ratio = (
            market_data.get('balance', settings.INITIAL_BALANCE) / 
            market_data.get('initial_balance', settings.INITIAL_BALANCE) - 1.0
        )
        
        # Create observation array (must match environment's observation space)
        # Note: environment.py uses raw values (no scaling), so we must match that.
        
        # Base features (12)
        obs_base = [
            float(close),
            float(market_data.get('volume', 0)),
            float(market_data.get('rsi', 50.0)),
            float(market_data.get('macd', 0.0)),
            float(market_data.get('signal', 0.0)),
            float(market_data.get('bb_upper', close)),
            float(market_data.get('bb_lower', close)),
            float(market_data.get('atr', 0.0)),
            float(position_ratio),
            float(market_data.get('position_size', 0)),
            float(entry_price),
            float(unrealized_pnl)
        ]
        
        # Stochastic features (6)
        obs_stoch = [
            float(market_data.get('stoch_k_fast', 50.0)),
            float(market_data.get('stoch_d_fast', 50.0)),
            float(market_data.get('stoch_k_mid', 50.0)),
            float(market_data.get('stoch_d_mid', 50.0)),
            float(market_data.get('stoch_k_slow', 50.0)),
            float(market_data.get('stoch_d_slow', 50.0))
        ]
        
        obs = np.array(obs_base + obs_stoch, dtype=np.float32)
        
        return obs
    
    def get_model_info(self) -> Dict:
        """Get model information"""
        if self.model is None:
            return {"status": "no_model_loaded"}
        
        return {
            "status": "loaded",
            "model_path": self.model_path,
            "learning_rate": self.learning_rate,
            "gamma": self.gamma,
            "batch_size": self.batch_size,
            "n_epochs": self.n_epochs,
            "device": str(self.model.device),
            "training_episodes": len(self.training_history['episodes'])
        }
