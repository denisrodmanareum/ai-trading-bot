"""
Backtest Engine
Automated backtesting system for strategy validation
"""
from typing import Dict, List
import numpy as np
import pandas as pd
from loguru import logger
from datetime import datetime


class BacktestEngine:
    """
    자동화된 백테스트 엔진
    - 전략 백테스트
    - A/B 테스트
    - 파라미터 최적화 지원
    """
    
    def __init__(self, binance_client):
        self.binance_client = binance_client
    
    async def run_backtest(
        self,
        symbol: str,
        strategy_config: Dict,
        start_date: str,
        end_date: str,
        initial_balance: float = 10000.0
    ) -> Dict:
        """
        백테스트 실행
        
        Returns:
            {
                'total_return': float,
                'sharpe_ratio': float,
                'max_drawdown': float,
                'win_rate': float,
                'total_trades': int,
                'avg_trade_duration': float,
                'profit_factor': float
            }
        """
        try:
            logger.info(f"Starting backtest: {symbol} from {start_date} to {end_date}")
            
            # 히스토리 데이터 로드
            df = await self.load_historical_data(symbol, start_date, end_date)
            
            if df is None or len(df) < 100:
                logger.warning("Insufficient data for backtest")
                return self._empty_result()
            
            # 전략 시뮬레이션
            results = await self.simulate_strategy(df, strategy_config, initial_balance)
            
            logger.info(f"Backtest complete: {results['total_trades']} trades, "
                       f"{results['total_return']*100:.2f}% return")
            
            return results
            
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            return self._empty_result()
    
    async def load_historical_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = '1m'
    ) -> pd.DataFrame:
        """히스토리 데이터 로드"""
        try:
            # 바이낸스에서 데이터 조회 (간단 버전)
            # 실제로는 대량 데이터 로드 로직 필요
            df = await self.binance_client.get_klines(symbol, interval, 1000)
            
            if df is not None:
                from ai.features import add_technical_indicators
                df = add_technical_indicators(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to load historical data: {e}")
            return None
    
    async def simulate_strategy(
        self,
        df: pd.DataFrame,
        strategy_config: Dict,
        initial_balance: float
    ) -> Dict:
        """전략 시뮬레이션"""
        try:
            balance = initial_balance
            position = None  # {'side': 'LONG/SHORT', 'entry_price': float, 'qty': float}
            trades = []
            balance_history = [balance]
            
            for i in range(len(df)):
                current_price = df['close'].iloc[i]
                
                # 전략 신호 생성 (간단 버전)
                signal = self._generate_signal(df.iloc[:i+1], strategy_config)
                
                # 포지션 없음 + 진입 신호
                if position is None and signal in ['LONG', 'SHORT']:
                    # 진입
                    position = {
                        'side': signal,
                        'entry_price': current_price,
                        'entry_index': i,
                        'qty': balance * 0.1 / current_price  # 10% 사용
                    }
                
                # 포지션 있음 + 청산 신호
                elif position and signal == 'CLOSE':
                    # 청산
                    exit_price = current_price
                    
                    if position['side'] == 'LONG':
                        pnl = (exit_price - position['entry_price']) * position['qty']
                    else:
                        pnl = (position['entry_price'] - exit_price) * position['qty']
                    
                    balance += pnl
                    balance_history.append(balance)
                    
                    trades.append({
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'side': position['side'],
                        'pnl': pnl,
                        'duration': i - position['entry_index']
                    })
                    
                    position = None
            
            # 메트릭 계산
            metrics = self._calculate_metrics(trades, balance, initial_balance, balance_history)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            return self._empty_result()
    
    def _generate_signal(self, df_slice: pd.DataFrame, config: Dict) -> str:
        """신호 생성 (간단 버전)"""
        if len(df_slice) < 20:
            return 'HOLD'
        
        latest = df_slice.iloc[-1]
        
        # RSI 기반 간단 전략
        rsi = latest.get('rsi', 50)
        
        if rsi < 30:
            return 'LONG'
        elif rsi > 70:
            return 'SHORT'
        else:
            return 'HOLD'
    
    def _calculate_metrics(
        self,
        trades: List[Dict],
        final_balance: float,
        initial_balance: float,
        balance_history: List[float]
    ) -> Dict:
        """메트릭 계산"""
        if not trades:
            return self._empty_result()
        
        # 총 수익률
        total_return = (final_balance - initial_balance) / initial_balance
        
        # 승률
        wins = [t for t in trades if t['pnl'] > 0]
        win_rate = len(wins) / len(trades)
        
        # Sharpe ratio
        returns = [t['pnl'] / initial_balance for t in trades]
        sharpe = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        
        # Max drawdown
        balance_array = np.array(balance_history)
        running_max = np.maximum.accumulate(balance_array)
        drawdown = (balance_array - running_max) / running_max
        max_drawdown = np.min(drawdown)
        
        # 평균 거래 시간
        avg_duration = np.mean([t['duration'] for t in trades])
        
        # Profit factor
        total_profit = sum([t['pnl'] for t in wins])
        total_loss = abs(sum([t['pnl'] for t in trades if t['pnl'] < 0]))
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        
        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe * np.sqrt(252),  # Annualized
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_trades': len(trades),
            'avg_trade_duration': avg_duration,
            'profit_factor': profit_factor,
            'final_balance': final_balance
        }
    
    def _empty_result(self) -> Dict:
        """빈 결과"""
        return {
            'total_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'total_trades': 0,
            'avg_trade_duration': 0.0,
            'profit_factor': 0.0,
            'final_balance': 0.0
        }
    
    async def ab_test(
        self,
        symbol: str,
        config_a: Dict,
        config_b: Dict,
        start_date: str,
        end_date: str
    ) -> Dict:
        """
        A/B 테스트
        
        Returns:
            {
                'config_a_results': Dict,
                'config_b_results': Dict,
                'winner': str,
                'improvement': float
            }
        """
        results_a = await self.run_backtest(symbol, config_a, start_date, end_date)
        results_b = await self.run_backtest(symbol, config_b, start_date, end_date)
        
        # 승자 결정 (Sharpe ratio 기준)
        if results_a['sharpe_ratio'] > results_b['sharpe_ratio']:
            winner = 'A'
            improvement = (results_a['sharpe_ratio'] - results_b['sharpe_ratio']) / results_b['sharpe_ratio'] if results_b['sharpe_ratio'] != 0 else 0
        else:
            winner = 'B'
            improvement = (results_b['sharpe_ratio'] - results_a['sharpe_ratio']) / results_a['sharpe_ratio'] if results_a['sharpe_ratio'] != 0 else 0
        
        return {
            'config_a_results': results_a,
            'config_b_results': results_b,
            'winner': winner,
            'improvement_pct': improvement * 100
        }
