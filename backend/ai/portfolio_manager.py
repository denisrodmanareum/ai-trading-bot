"""
Portfolio Manager
Manages portfolio diversification and correlation analysis
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime, timedelta


class PortfolioManager:
    """
    포트폴리오 최적화 및 상관관계 관리
    - 코인 간 상관관계 계산
    - 분산 투자 검증
    - 포트폴리오 리밸런싱
    """
    
    def __init__(self, binance_client):
        self.binance_client = binance_client
        self.correlation_cache = {}  # symbol_pair -> correlation
        self.last_update = None
        self.cache_duration = timedelta(hours=1)  # 1시간마다 갱신
    
    async def calculate_correlation_matrix(
        self,
        symbols: List[str],
        interval: str = '1h',
        limit: int = 100
    ) -> pd.DataFrame:
        """
        코인 간 상관관계 행렬 계산
        
        Args:
            symbols: 심볼 리스트
            interval: 시간 간격
            limit: 캔들 개수
            
        Returns:
            Correlation matrix (DataFrame)
        """
        try:
            # 가격 데이터 수집
            price_data = {}
            
            for symbol in symbols:
                df = await self.binance_client.get_klines(symbol, interval, limit)
                if df is not None and len(df) > 0:
                    # 수익률 계산 (로그 수익률)
                    returns = np.log(df['close'] / df['close'].shift(1))
                    price_data[symbol] = returns.dropna()
            
            if len(price_data) < 2:
                logger.warning("Not enough symbols for correlation matrix")
                return pd.DataFrame()
            
            # DataFrame 생성
            price_df = pd.DataFrame(price_data)
            
            # 상관관계 행렬
            corr_matrix = price_df.corr()
            
            # 캐시 업데이트
            self.last_update = datetime.now()
            
            logger.info(f"📊 Correlation matrix calculated for {len(symbols)} symbols")
            
            return corr_matrix
            
        except Exception as e:
            logger.error(f"Failed to calculate correlation matrix: {e}")
            return pd.DataFrame()
    
    async def check_diversification(
        self,
        symbol: str,
        side: str,
        active_positions: List[Dict],
        max_correlation: float = 0.7
    ) -> Dict:
        """
        신규 진입이 포트폴리오 다각화에 도움이 되는지 체크
        
        Args:
            symbol: 진입하려는 심볼
            side: LONG or SHORT
            active_positions: 현재 활성 포지션 리스트
            max_correlation: 최대 허용 상관관계
            
        Returns:
            {
                'is_diversified': bool,
                'avg_correlation': float,
                'highly_correlated_with': List[str],
                'recommendation': str
            }
        """
        if len(active_positions) == 0:
            return {
                'is_diversified': True,
                'avg_correlation': 0.0,
                'highly_correlated_with': [],
                'recommendation': 'First position - OK'
            }
        
        try:
            # 같은 방향 포지션만 추출
            same_direction = [
                p for p in active_positions
                if (float(p.get('position_amt', 0)) > 0 and side == "LONG") or
                   (float(p.get('position_amt', 0)) < 0 and side == "SHORT")
            ]
            
            if len(same_direction) == 0:
                return {
                    'is_diversified': True,
                    'avg_correlation': 0.0,
                    'highly_correlated_with': [],
                    'recommendation': 'Opposite direction - OK'
                }
            
            # 심볼 목록
            existing_symbols = [p['symbol'] for p in same_direction]
            all_symbols = existing_symbols + [symbol]
            
            # 상관관계 행렬 계산
            corr_matrix = await self.calculate_correlation_matrix(all_symbols)
            
            if corr_matrix.empty:
                # 계산 실패 시 통과
                return {
                    'is_diversified': True,
                    'avg_correlation': 0.0,
                    'highly_correlated_with': [],
                    'recommendation': 'Correlation data unavailable - allowing trade'
                }
            
            # 신규 심볼과 기존 심볼들의 상관관계
            correlations = []
            highly_correlated = []
            
            for existing_symbol in existing_symbols:
                if existing_symbol in corr_matrix.columns and symbol in corr_matrix.index:
                    corr = abs(corr_matrix.loc[symbol, existing_symbol])
                    correlations.append(corr)
                    
                    if corr > max_correlation:
                        highly_correlated.append(f"{existing_symbol} ({corr:.2f})")
            
            # 평균 상관관계
            avg_corr = np.mean(correlations) if correlations else 0.0
            
            # 판단
            is_diversified = avg_corr <= max_correlation
            
            if is_diversified:
                recommendation = f"Good diversification (avg corr: {avg_corr:.2f})"
            else:
                recommendation = f"High correlation detected (avg: {avg_corr:.2f}). " \
                               f"Similar to: {', '.join(highly_correlated[:3])}"
            
            return {
                'is_diversified': is_diversified,
                'avg_correlation': float(avg_corr),
                'highly_correlated_with': highly_correlated,
                'recommendation': recommendation
            }
            
        except Exception as e:
            logger.error(f"Diversification check failed: {e}")
            # 에러 시 통과 (안전하게)
            return {
                'is_diversified': True,
                'avg_correlation': 0.0,
                'highly_correlated_with': [],
                'recommendation': 'Check failed - allowing trade'
            }
    
    def get_portfolio_metrics(self, positions: List[Dict]) -> Dict:
        """
        포트폴리오 메트릭 계산
        
        Returns:
            {
                'total_positions': int,
                'long_count': int,
                'short_count': int,
                'long_ratio': float,
                'total_notional': float,
                'largest_position_pct': float
            }
        """
        if not positions:
            return {
                'total_positions': 0,
                'long_count': 0,
                'short_count': 0,
                'long_ratio': 0.0,
                'total_notional': 0.0,
                'largest_position_pct': 0.0
            }
        
        long_count = 0
        short_count = 0
        notionals = []
        
        for pos in positions:
            amt = float(pos.get('position_amt', 0))
            if amt > 0:
                long_count += 1
            elif amt < 0:
                short_count += 1
            
            # Notional value
            entry_price = float(pos.get('entry_price', 0))
            notional = abs(amt * entry_price)
            notionals.append(notional)
        
        total_positions = long_count + short_count
        long_ratio = long_count / total_positions if total_positions > 0 else 0.0
        total_notional = sum(notionals)
        largest_position_pct = max(notionals) / total_notional if total_notional > 0 else 0.0
        
        return {
            'total_positions': total_positions,
            'long_count': long_count,
            'short_count': short_count,
            'long_ratio': long_ratio,
            'short_ratio': 1 - long_ratio,
            'total_notional': total_notional,
            'largest_position_pct': largest_position_pct,
            'avg_position_size': total_notional / total_positions if total_positions > 0 else 0.0
        }
    
    async def suggest_rebalance(self, positions: List[Dict]) -> Dict:
        """
        포트폴리오 리밸런싱 제안
        
        Returns:
            {
                'needs_rebalance': bool,
                'reason': str,
                'suggestions': List[str]
            }
        """
        metrics = self.get_portfolio_metrics(positions)
        
        suggestions = []
        needs_rebalance = False
        reason = ""
        
        # 1. 방향 편중 체크 (75:25 법칙)
        if metrics['long_ratio'] > 0.75:
            needs_rebalance = True
            reason = f"LONG positions too concentrated ({metrics['long_ratio']*100:.0f}%)"
            suggestions.append("Consider taking SHORT positions for balance")
        elif metrics['long_ratio'] < 0.25:
            needs_rebalance = True
            reason = f"SHORT positions too concentrated ({metrics['short_ratio']*100:.0f}%)"
            suggestions.append("Consider taking LONG positions for balance")
        
        # 2. 단일 포지션 집중도 체크 (30% 이상이면 경고)
        if metrics['largest_position_pct'] > 0.3:
            needs_rebalance = True
            reason = f"Single position too large ({metrics['largest_position_pct']*100:.0f}%)"
            suggestions.append("Consider reducing largest position size")
        
        # 3. 상관관계 체크 (모든 포지션)
        if len(positions) >= 3:
            symbols = [p['symbol'] for p in positions]
            corr_matrix = await self.calculate_correlation_matrix(symbols)
            
            if not corr_matrix.empty:
                # 평균 상관관계
                avg_corr = corr_matrix.abs().values[np.triu_indices_from(corr_matrix.values, 1)].mean()
                
                if avg_corr > 0.7:
                    needs_rebalance = True
                    reason = f"High average correlation ({avg_corr:.2f})"
                    suggestions.append("Portfolio lacks diversification - consider uncorrelated assets")
        
        if not needs_rebalance:
            reason = "Portfolio is well balanced"
            suggestions = ["No action needed"]
        
        return {
            'needs_rebalance': needs_rebalance,
            'reason': reason,
            'suggestions': suggestions,
            'metrics': metrics
        }
