"""
Parameter Optimizer
Automated parameter optimization using Bayesian optimization
"""
from typing import Dict, List, Tuple
import numpy as np
from loguru import logger


class ParameterOptimizer:
    """
    파라미터 자동 최적화
    - Grid search
    - Random search
    - Bayesian optimization (simple)
    """
    
    def __init__(self, backtest_engine):
        self.backtest_engine = backtest_engine
    
    async def grid_search(
        self,
        symbol: str,
        param_grid: Dict[str, List],
        start_date: str,
        end_date: str
    ) -> Dict:
        """
        그리드 서치
        
        Args:
            param_grid: {'param_name': [value1, value2, ...]}
            
        Returns:
            Best parameters and results
        """
        try:
            logger.info(f"Starting grid search with {len(param_grid)} parameters")
            
            # 모든 조합 생성
            param_combinations = self._generate_combinations(param_grid)
            
            logger.info(f"Testing {len(param_combinations)} combinations")
            
            best_score = -np.inf
            best_params = None
            best_results = None
            
            for i, params in enumerate(param_combinations):
                logger.info(f"Testing combination {i+1}/{len(param_combinations)}: {params}")
                
                # 백테스트 실행
                results = await self.backtest_engine.run_backtest(
                    symbol,
                    params,
                    start_date,
                    end_date
                )
                
                # Sharpe ratio로 평가
                score = results['sharpe_ratio']
                
                if score > best_score:
                    best_score = score
                    best_params = params
                    best_results = results
                    logger.info(f"✅ New best: Sharpe={score:.3f}")
            
            return {
                'best_params': best_params,
                'best_results': best_results,
                'best_score': best_score,
                'tested_combinations': len(param_combinations)
            }
            
        except Exception as e:
            logger.error(f"Grid search failed: {e}")
            return {}
    
    def _generate_combinations(self, param_grid: Dict) -> List[Dict]:
        """파라미터 조합 생성"""
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        
        combinations = []
        
        def backtrack(index, current):
            if index == len(keys):
                combinations.append(current.copy())
                return
            
            for value in values[index]:
                current[keys[index]] = value
                backtrack(index + 1, current)
        
        backtrack(0, {})
        return combinations
    
    async def random_search(
        self,
        symbol: str,
        param_ranges: Dict[str, Tuple[float, float]],
        n_iterations: int,
        start_date: str,
        end_date: str
    ) -> Dict:
        """
        랜덤 서치
        
        Args:
            param_ranges: {'param_name': (min, max)}
            n_iterations: 시도 횟수
        """
        try:
            logger.info(f"Starting random search with {n_iterations} iterations")
            
            best_score = -np.inf
            best_params = None
            best_results = None
            
            for i in range(n_iterations):
                # 랜덤 파라미터 생성
                params = {}
                for key, (min_val, max_val) in param_ranges.items():
                    params[key] = np.random.uniform(min_val, max_val)
                
                logger.info(f"Iteration {i+1}/{n_iterations}: {params}")
                
                # 백테스트
                results = await self.backtest_engine.run_backtest(
                    symbol,
                    params,
                    start_date,
                    end_date
                )
                
                score = results['sharpe_ratio']
                
                if score > best_score:
                    best_score = score
                    best_params = params
                    best_results = results
                    logger.info(f"✅ New best: Sharpe={score:.3f}")
            
            return {
                'best_params': best_params,
                'best_results': best_results,
                'best_score': best_score,
                'iterations': n_iterations
            }
            
        except Exception as e:
            logger.error(f"Random search failed: {e}")
            return {}
    
    async def optimize_current_strategy(
        self,
        symbol: str = "BTCUSDT",
        days: int = 30
    ) -> Dict:
        """
        현재 전략 최적화
        주요 파라미터 자동 튜닝
        """
        from datetime import datetime, timedelta
        
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        # 주요 파라미터 범위
        param_ranges = {
            'oversold': (20, 30),
            'overbought': (70, 80),
            'rsi_threshold': (25, 35),
            'tp_multiplier': (3.0, 9.0),
            'sl_multiplier': (1.5, 3.5)
        }
        
        # 랜덤 서치 실행
        results = await self.random_search(
            symbol,
            param_ranges,
            n_iterations=20,
            start_date=start_date,
            end_date=end_date
        )
        
        return results
