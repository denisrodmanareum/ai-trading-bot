import optuna
import os
import numpy as np
import pandas as pd
from loguru import logger
from typing import Dict, Any, Optional
from datetime import datetime

from ai.agent import TradingAgent
from app.core.config import settings

class AIOptimizer:
    """Auto-tuning for Trading Agent using Optuna"""

    def __init__(self, data_path: str = "data/market_data.csv"):
        self.data_path = data_path
        self.study: Optional[optuna.study.Study] = None
        self.best_params: Dict[str, Any] = {}
        self.is_optimizing = False

    def load_data(self) -> pd.DataFrame:
        """Load data for optimization"""
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"Data file not found: {self.data_path}")
        
        df = pd.read_csv(self.data_path)
        # Ensure timestamp alignment if needed, or simple cleaning
        return df

    def objective(self, trial: optuna.Trial):
        """Optuna objective function"""
        try:
            # 1. Sample Hyperparameters
            learning_rate = trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True)
            gamma = trial.suggest_categorical("gamma", [0.9, 0.95, 0.98, 0.99])
            batch_size = trial.suggest_categorical("batch_size", [64, 128, 256])
            ent_coef = trial.suggest_float("ent_coef", 1e-8, 1e-1, log=True)
            n_epochs = trial.suggest_int("n_epochs", 3, 10)
            
            # 2. Init Agent with params
            agent = TradingAgent(
                learning_rate=learning_rate,
                gamma=gamma,
                batch_size=batch_size,
                n_epochs=n_epochs
            )
            
            # Load Data (Optimize on a subset for speed? Let's use full for now or last 1000 candles)
            # For speed, let's limit to recent data
            df = self.load_data()
            if len(df) > 2000:
                df = df.iloc[-2000:].reset_index(drop=True)
                
            env = agent.create_environment(df)
            agent.build_model(env)
            
            # Override ent_coef in model if accessible, or passed in build
            if agent.model:
                agent.model.ent_coef = ent_coef

            # 3. Short Training
            # Train for limited steps (e.g. 10000) to gauge performance
            total_timesteps = 5000 
            agent.model.learn(total_timesteps=total_timesteps)
            
            # 4. Evaluate
            # Run a validation episode
            obs = env.reset()
            done = False
            total_reward = 0
            
            while not done:
                action, _ = agent.model.predict(obs, deterministic=True)
                obs, reward, done, info = env.step(action)
                total_reward += reward
                
            # Metric: Total Reward
            return total_reward
            
        except Exception as e:
            logger.error(f"Trial failed: {e}")
            raise optuna.exceptions.TrialPruned()

    async def run_optimization(self, n_trials: int = 10):
        """Run the optimization study"""
        if self.is_optimizing:
            logger.warning("Optimization already in progress")
            return

        logger.info(f"Starting Hyperparameter Optimization (Trials: {n_trials})")
        self.is_optimizing = True
        
        try:
            # Create Study
            self.study = optuna.create_study(
                direction="maximize",
                study_name=f"ppo_tuning_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                storage=f"sqlite:///data/optuna.db", # Persist results
                load_if_exists=True
            )
            
            # Optimize (Blocking call, might need to run in executor for async API)
            # For simplicity in this step, we run it directly, but ideally in a background thread/process
            self.study.optimize(self.objective, n_trials=n_trials)
            
            self.best_params = self.study.best_params
            logger.info("✅ Optimization Completed")
            logger.info(f"Best Params: {self.best_params}")
            logger.info(f"Best Value: {self.study.best_value}")
            
            # Save best params to a config file?
            self._save_best_params()
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
        finally:
            self.is_optimizing = False

    def _save_best_params(self):
        """Save best parameters to JSON"""
        import json
        try:
            path = "data/best_params.json"
            with open(path, "w") as f:
                json.dump(self.best_params, f, indent=4)
            logger.info(f"Saved best params to {path}")
        except Exception as e:
            logger.error(f"Failed to save params: {e}")
