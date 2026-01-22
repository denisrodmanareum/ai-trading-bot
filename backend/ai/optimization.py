"""
Hyperparameter Optimization for PPO Trading Agent
FIXED VERSION - All issues resolved
"""
import optuna
import os
import torch
import numpy as np
import pandas as pd
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from loguru import logger

from ai.agent import TradingAgent
from ai.environment import TradingEnvironment
from ai.features import add_technical_indicators


class HyperOptimizer:
    """
    Hyperparameter Optimizer using Optuna
    """
    
    def __init__(
        self, 
        data_path: str = "data/train_data.csv",
        n_trials: int = 10,
        db_url: str = "sqlite:///data/optimization.db",
        study_name: str = "ppo_optimization"
    ):
        self.data_path = data_path
        self.n_trials = n_trials
        self.db_url = db_url
        self.study_name = study_name
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_url.replace("sqlite:///", "")), exist_ok=True)
        
    def objective(self, trial: optuna.Trial) -> float:
        """
        Objective function for optimization
        Returns: Total reward (to maximize)
        """
        try:
            # 1. Suggest Hyperparameters
            learning_rate = trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True)
            n_steps = trial.suggest_categorical("n_steps", [1024, 2048, 4096])
            batch_size = trial.suggest_categorical("batch_size", [64, 128, 256])
            gamma = trial.suggest_float("gamma", 0.90, 0.999)
            ent_coef = trial.suggest_float("ent_coef", 0.00001, 0.01, log=True)
            n_epochs = trial.suggest_int("n_epochs", 5, 20)
            
            logger.info(f"Trial {trial.number}: LR={learning_rate:.6f}, Steps={n_steps}, Batch={batch_size}")
            
            # 2. Load and prepare data
            if not os.path.exists(self.data_path):
                logger.error(f"Data file not found: {self.data_path}")
                raise optuna.exceptions.TrialPruned()
            
            df = pd.read_csv(self.data_path)
            
            # Add indicators if not present
            if 'rsi' not in df.columns:
                df = add_technical_indicators(df)
            
            # 3. Create environment
            env = TradingEnvironment(
                df=df,
                initial_balance=10000.0,
                leverage=5,
                commission=0.0004
            )
            
            vec_env = DummyVecEnv([lambda: env])
            
            # 4. Create PPO model with trial parameters
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            model = PPO(
                "MlpPolicy",
                vec_env,
                learning_rate=learning_rate,
                n_steps=n_steps,
                batch_size=batch_size,
                gamma=gamma,
                ent_coef=ent_coef,
                n_epochs=n_epochs,
                verbose=0,
                device=device
            )
            
            # 5. Short training (for optimization speed)
            total_timesteps = n_steps * 5  # 5 updates
            model.learn(total_timesteps=total_timesteps, progress_bar=False)
            
            # 6. Evaluate
            obs = vec_env.reset()
            done = False
            total_reward = 0.0
            steps = 0
            max_steps = len(df) - 1
            
            while not done and steps < max_steps:
                action, _states = model.predict(obs, deterministic=True)
                obs, reward, done, info = vec_env.step(action)
                total_reward += reward[0]
                steps += 1
            
            # Get final balance as additional metric
            final_balance = env.balance
            balance_ratio = final_balance / env.initial_balance
            
            # Combined score: reward + balance performance
            score = total_reward + (balance_ratio - 1.0) * 100
            
            logger.info(
                f"Trial {trial.number} complete: "
                f"Reward={total_reward:.2f}, Balance={final_balance:.2f}, Score={score:.2f}"
            )
            
            return score
            
        except Exception as e:
            logger.error(f"Trial {trial.number} failed: {e}")
            raise optuna.exceptions.TrialPruned()
    
    def run_optimization(self):
        """
        Run hyperparameter optimization
        
        Returns:
            best_params (dict): Best hyperparameters found
            best_value (float): Best score achieved
        """
        logger.info(f"🔍 Starting Optimization: {self.n_trials} trials")
        logger.info(f"📊 Database: {self.db_url}")
        logger.info(f"📁 Data: {self.data_path}")
        
        # Create study
        study = optuna.create_study(
            study_name=self.study_name,
            storage=self.db_url,
            direction="maximize",
            load_if_exists=True
        )
        
        # Run optimization
        study.optimize(
            self.objective,
            n_trials=self.n_trials,
            show_progress_bar=True,
            n_jobs=1  # Sequential for stability
        )
        
        # Log results
        logger.success("✅ Optimization Complete!")
        logger.info(f"🏆 Best Params: {study.best_params}")
        logger.info(f"📈 Best Value: {study.best_value:.2f}")
        
        # Check if best_trial exists
        if study.best_trial is None:
            logger.warning("⚠️ No successful trials completed")
            return {}, 0.0
        
        return study.best_params, study.best_value
    
    def get_study_summary(self) -> dict:
        """
        Get summary of optimization study
        
        Returns:
            dict: Study statistics
        """
        try:
            study = optuna.load_study(
                study_name=self.study_name,
                storage=self.db_url
            )
            
            completed_trials = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
            
            if not completed_trials:
                return {
                    "total_trials": len(study.trials),
                    "completed_trials": 0,
                    "pruned_trials": len([t for t in study.trials if t.state == optuna.trial.TrialState.PRUNED]),
                    "failed_trials": len([t for t in study.trials if t.state == optuna.trial.TrialState.FAIL])
                }
            
            return {
                "total_trials": len(study.trials),
                "completed_trials": len(completed_trials),
                "pruned_trials": len([t for t in study.trials if t.state == optuna.trial.TrialState.PRUNED]),
                "failed_trials": len([t for t in study.trials if t.state == optuna.trial.TrialState.FAIL]),
                "best_value": study.best_value,
                "best_params": study.best_params,
                "best_trial_number": study.best_trial.number
            }
            
        except Exception as e:
            logger.error(f"Failed to get study summary: {e}")
            return {}


def optimize_hyperparameters(
    data_path: str,
    n_trials: int = 10,
    study_name: str = "ppo_optimization"
) -> tuple:
    """
    Convenience function for hyperparameter optimization
    
    Args:
        data_path: Path to training data CSV
        n_trials: Number of optimization trials
        study_name: Name for Optuna study
        
    Returns:
        (best_params, best_value): Tuple of best parameters and score
    """
    optimizer = HyperOptimizer(
        data_path=data_path,
        n_trials=n_trials,
        study_name=study_name
    )
    
    return optimizer.run_optimization()
