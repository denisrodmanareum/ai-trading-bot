"""
Self-Learning System
AI automatically learns from its own trading history and improves over time
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from pathlib import Path
import json

from stable_baselines3 import PPO
from ai.environment import TradingEnvironment
from ai.rewards import get_reward_strategy
from ai.features import add_technical_indicators


class SelfLearningSystem:
    """
    Continuously learns from trading history
    - Collects real trading data
    - Retrains models periodically
    - Tracks performance improvements
    - Adjusts strategy parameters
    """
    
    def __init__(
        self,
        model_dir: str = "data/models",
        training_data_dir: str = "data/training",
        min_samples_for_retrain: int = 100,
        retrain_frequency_days: int = 7
    ):
        self.model_dir = Path(model_dir)
        self.training_data_dir = Path(training_data_dir)
        self.min_samples_for_retrain = min_samples_for_retrain
        self.retrain_frequency_days = retrain_frequency_days
        
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.training_data_dir.mkdir(parents=True, exist_ok=True)
        
        self.learning_history = []
        self.performance_tracking = {
            'iterations': [],
            'win_rates': [],
            'avg_rewards': [],
            'sharpe_ratios': []
        }
    
    def collect_trading_data(
        self,
        trades: List[Dict],
        market_data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Collect and format trading data for retraining
        
        Args:
            trades: List of executed trades
            market_data: Historical market data (OHLCV)
        
        Returns:
            DataFrame ready for training
        """
        try:
            # Merge trades with market data
            df = market_data.copy()
            
            # Add technical indicators
            df = add_technical_indicators(df)
            
            # Add trade outcomes
            df['action'] = 0  # Default HOLD
            df['pnl'] = 0.0
            df['reward'] = 0.0
            
            for trade in trades:
                # Find corresponding timestamp in df
                trade_time = pd.to_datetime(trade['timestamp'])
                
                # Find nearest index
                idx = df.index[df.index.get_indexer([trade_time], method='nearest')[0]]
                
                # Mark action
                if trade['side'] == 'LONG':
                    df.loc[idx, 'action'] = 1
                elif trade['side'] == 'SHORT':
                    df.loc[idx, 'action'] = 2
                elif trade['side'] == 'CLOSE':
                    df.loc[idx, 'action'] = 3
                
                # Add PnL
                df.loc[idx, 'pnl'] = trade.get('pnl', 0)
            
            # Calculate rewards using improved reward function
            reward_calc = get_reward_strategy("improved")
            
            for i in range(len(df)):
                action = df.iloc[i]['action']
                pnl = df.iloc[i]['pnl']
                
                # Simplified balance tracking
                balance = 10000 + df.iloc[:i+1]['pnl'].sum()
                
                reward = reward_calc.calculate(
                    action=action,
                    pnl=pnl,
                    position_size=0.1,  # Placeholder
                    balance=balance
                )
                
                df.at[df.index[i], 'reward'] = reward
            
            # Save collected data
            filename = self.training_data_dir / f"collected_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename)
            logger.info(f"Collected {len(trades)} trades, saved to {filename}")
            
            return df
            
        except Exception as e:
            logger.error(f"Data collection failed: {e}")
            return pd.DataFrame()
    
    def should_retrain(self) -> bool:
        """
        Determine if model should be retrained
        
        Checks:
        - Enough new samples collected
        - Time since last training
        - Performance degradation
        """
        # Check if enough data
        all_data_files = list(self.training_data_dir.glob("collected_*.csv"))
        
        if len(all_data_files) == 0:
            return False
        
        # Count total samples
        total_samples = 0
        for file in all_data_files:
            df = pd.read_csv(file)
            total_samples += len(df[df['action'] != 0])  # Count actual trades
        
        if total_samples < self.min_samples_for_retrain:
            logger.info(f"Not enough samples for retrain: {total_samples}/{self.min_samples_for_retrain}")
            return False
        
        # Check time since last training
        if self.learning_history:
            last_training = datetime.fromisoformat(self.learning_history[-1]['timestamp'])
            days_since = (datetime.now() - last_training).days
            
            if days_since < self.retrain_frequency_days:
                logger.info(f"Too soon to retrain: {days_since}/{self.retrain_frequency_days} days")
                return False
        
        logger.info(f"Ready to retrain: {total_samples} samples available")
        return True
    
    def retrain_model(
        self,
        symbol: str = "BTCUSDT",
        total_timesteps: int = 50000
    ) -> Dict:
        """
        Retrain the model with collected data
        
        Returns:
            {
                'success': bool,
                'model_path': str,
                'performance': dict,
                'improvements': dict
            }
        """
        try:
            logger.info(f"Starting model retraining for {symbol}...")
            
            # Load all collected data
            all_data_files = sorted(self.training_data_dir.glob("collected_*.csv"))
            
            if not all_data_files:
                raise ValueError("No training data available")
            
            # Merge all data
            dfs = []
            for file in all_data_files[-10:]:  # Use last 10 files to avoid memory issues
                df = pd.read_csv(file, index_col=0)
                dfs.append(df)
            
            combined_df = pd.concat(dfs, ignore_index=True)
            logger.info(f"Loaded {len(combined_df)} samples from {len(dfs)} files")
            
            # Create training environment
            env = TradingEnvironment(
                df=combined_df,
                initial_balance=10000.0,
                leverage=5,
                reward_strategy="improved",
                use_stochastic=True
            )
            
            # Load previous model if exists
            latest_model = self._get_latest_model(symbol)
            
            if latest_model:
                logger.info(f"Loading existing model: {latest_model}")
                model = PPO.load(latest_model, env=env)
            else:
                logger.info("Creating new model")
                model = PPO(
                    "MlpPolicy",
                    env,
                    verbose=1,
                    learning_rate=0.0003,
                    n_steps=2048,
                    batch_size=64,
                    n_epochs=10,
                    gamma=0.99,
                    gae_lambda=0.95,
                    clip_range=0.2,
                    tensorboard_log="data/tensorboard"
                )
            
            # Train
            logger.info(f"Training for {total_timesteps} timesteps...")
            model.learn(total_timesteps=total_timesteps)
            
            # Save new model
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            model_path = self.model_dir / f"ppo_trading_{symbol}_{timestamp}_retrained.zip"
            model.save(str(model_path))
            logger.info(f"Model saved to {model_path}")
            
            # Evaluate performance
            performance = self._evaluate_model(model, env)
            
            # Track improvements
            improvements = self._calculate_improvements(performance)
            
            # Record learning event
            learning_record = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'model_path': str(model_path),
                'total_timesteps': total_timesteps,
                'training_samples': len(combined_df),
                'performance': performance,
                'improvements': improvements
            }
            
            self.learning_history.append(learning_record)
            self._save_learning_history()
            
            logger.info(f"✅ Retraining completed! Win rate: {performance['win_rate']:.1%}, Avg reward: {performance['avg_reward']:.3f}")
            
            return {
                'success': True,
                'model_path': str(model_path),
                'performance': performance,
                'improvements': improvements
            }
            
        except Exception as e:
            logger.error(f"Retraining failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_latest_model(self, symbol: str) -> Optional[Path]:
        """Get the latest trained model for a symbol"""
        model_files = list(self.model_dir.glob(f"ppo_trading_{symbol}_*.zip"))
        
        if not model_files:
            return None
        
        # Sort by modification time
        latest = max(model_files, key=lambda p: p.stat().st_mtime)
        return latest
    
    def _evaluate_model(self, model: PPO, env: TradingEnvironment) -> Dict:
        """
        Evaluate model performance
        """
        try:
            obs, _ = env.reset()
            
            total_reward = 0
            wins = 0
            losses = 0
            trades = 0
            
            for _ in range(1000):  # Run 1000 steps
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, done, truncated, info = env.step(action)
                
                total_reward += reward
                
                # Count trades
                if action in [1, 2]:  # LONG or SHORT
                    trades += 1
                    if reward > 0:
                        wins += 1
                    else:
                        losses += 1
                
                if done or truncated:
                    obs, _ = env.reset()
            
            win_rate = wins / trades if trades > 0 else 0
            avg_reward = total_reward / 1000
            
            return {
                'win_rate': win_rate,
                'avg_reward': avg_reward,
                'total_trades': trades,
                'wins': wins,
                'losses': losses
            }
            
        except Exception as e:
            logger.error(f"Model evaluation failed: {e}")
            return {
                'win_rate': 0,
                'avg_reward': 0,
                'total_trades': 0
            }
    
    def _calculate_improvements(self, current_performance: Dict) -> Dict:
        """
        Calculate improvements compared to previous iteration
        """
        if not self.learning_history:
            return {
                'win_rate_delta': 0,
                'reward_delta': 0,
                'message': 'First training iteration'
            }
        
        prev_performance = self.learning_history[-1]['performance']
        
        wr_delta = current_performance['win_rate'] - prev_performance['win_rate']
        reward_delta = current_performance['avg_reward'] - prev_performance['avg_reward']
        
        return {
            'win_rate_delta': round(wr_delta, 3),
            'reward_delta': round(reward_delta, 3),
            'message': 'Improved' if wr_delta > 0 or reward_delta > 0 else 'No improvement'
        }
    
    def _save_learning_history(self):
        """Save learning history to file"""
        try:
            history_file = self.model_dir / "learning_history.json"
            with open(history_file, 'w') as f:
                json.dump(self.learning_history, f, indent=2)
            logger.info(f"Learning history saved to {history_file}")
        except Exception as e:
            logger.error(f"Failed to save learning history: {e}")
    
    def get_learning_progress(self) -> Dict:
        """
        Get overview of learning progress
        """
        if not self.learning_history:
            return {
                'total_iterations': 0,
                'message': 'No training iterations yet'
            }
        
        iterations = len(self.learning_history)
        
        # Extract performance metrics
        win_rates = [h['performance']['win_rate'] for h in self.learning_history]
        avg_rewards = [h['performance']['avg_reward'] for h in self.learning_history]
        
        return {
            'total_iterations': iterations,
            'latest_win_rate': win_rates[-1],
            'latest_avg_reward': avg_rewards[-1],
            'best_win_rate': max(win_rates),
            'best_avg_reward': max(avg_rewards),
            'trend': 'improving' if win_rates[-1] > win_rates[0] else 'declining',
            'history': self.learning_history
        }
