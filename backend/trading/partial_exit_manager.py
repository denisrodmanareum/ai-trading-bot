"""
Partial Exit Manager
Manages scaled exits for better profit realization
"""
from typing import Dict, List, Optional
from loguru import logger
import time


class PartialExitManager:
    """
    단계별 익절 관리 시스템
    - SCALP: 3단계 익절
    - SWING: 4단계 익절
    - 첫 익절 후 SL을 본전으로 이동
    """
    
    def __init__(self):
        # SCALP 모드: 더 공격적인 3단계 익절 (0.8%→1.5% 시작)
        self.scalp_levels = [
            {'pct': 1.5, 'exit': 0.2, 'name': 'Level1'},   # +1.5% → 20% 청산 (노이즈 방지)
            {'pct': 3.0, 'exit': 0.3, 'name': 'Level2'},   # +3.0% → 30% 추가
            {'pct': 5.0, 'exit': 1.0, 'name': 'Level3'}    # +5.0% → 전량 익절
        ]
        
        # SWING 모드: 추세 추종형 4단계 익절
        self.swing_levels = [
            {'pct': 3.0, 'exit': 0.25, 'name': 'Level1'},  # +3% → 25% 청산
            {'pct': 6.0, 'exit': 0.25, 'name': 'Level2'},  # +6% → 25% 추가
            {'pct': 10.0, 'exit': 0.3, 'name': 'Level3'},  # +10% → 30% 추가
            {'pct': 20.0, 'exit': 1.0, 'name': 'Level4'}   # +20% → 전량 익절 (잭팟)
        ]
        
        # 심볼별 익절 상태 추적
        self.exit_states = {}  # symbol -> {level1: bool, level2: bool, ...}
    
    def initialize_symbol(self, symbol: str, mode: str):
        """심볼 익절 상태 초기화"""
        self.exit_states[symbol] = {
            'mode': mode,
            'levels_completed': set(),
            'breakeven_set': False,
            'first_exit_time': None
        }
    
    def clear_symbol(self, symbol: str):
        """심볼 상태 제거"""
        if symbol in self.exit_states:
            del self.exit_states[symbol]
    
    async def check_partial_exits(
        self,
        symbol: str,
        bracket: Dict,
        current_price: float,
        exchange_client
    ) -> Optional[Dict]:
        """
        부분 청산 체크 및 실행
        
        Returns:
            {
                'level': str,
                'exit_pct': float,
                'exit_qty': float,
                'pnl_pct': float
            } or None
        """
        if symbol not in self.exit_states:
            return None
        
        state = self.exit_states[symbol]
        mode = state['mode']
        
        # 레벨 선택
        levels = self.scalp_levels if mode == "SCALP" else self.swing_levels
        
        # 브래킷 정보 추출
        entry_price = bracket.get('entry_price', 0)
        side = bracket.get('side')
        initial_qty = bracket.get('initial_qty', bracket.get('qty', 0))
        current_qty = bracket.get('qty', 0)
        leverage = bracket.get('leverage', 5)
        
        if entry_price == 0 or current_qty == 0:
            return None
        
        # 수익률 계산 (레버리지 고려)
        if side == "LONG":
            pnl_pct = (current_price - entry_price) / entry_price * 100 * leverage
        elif side == "SHORT":
            pnl_pct = (entry_price - current_price) / entry_price * 100 * leverage
        else:
            return None
        
        # 각 레벨 체크
        for level in levels:
            level_key = level['name']
            
            # 이미 완료한 레벨은 스킵
            if level_key in state['levels_completed']:
                continue
            
            # 목표 수익률 도달 체크
            if pnl_pct >= level['pct']:
                # 청산 수량 계산
                if level['exit'] == 1.0:
                    # 마지막 레벨 - 전부 청산
                    exit_qty = current_qty
                else:
                    # 초기 수량 기준으로 계산
                    exit_qty = initial_qty * level['exit']
                    
                    # 현재 남은 수량보다 많으면 조정
                    if exit_qty > current_qty:
                        exit_qty = current_qty
                
                # 최소 수량 체크
                if exit_qty < 0.001:
                    logger.debug(f"Exit quantity too small: {exit_qty}")
                    continue
                
                # 부분 청산 실행
                try:
                    logger.info(
                        f"💰 Partial Exit {symbol} {level_key}: "
                        f"{level['exit']*100:.0f}% at +{pnl_pct:.2f}% "
                        f"(Qty: {exit_qty:.4f})"
                    )
                    
                    close_side = "SELL" if side == "LONG" else "BUY"
                    order = await exchange_client.place_market_order(
                        symbol,
                        close_side,
                        exit_qty
                    )
                    
                    # 상태 업데이트
                    state['levels_completed'].add(level_key)
                    
                    # 첫 청산 시간 기록
                    if state['first_exit_time'] is None:
                        state['first_exit_time'] = time.time()
                    
                    # 브래킷의 남은 수량 업데이트
                    bracket['qty'] = current_qty - exit_qty
                    
                    return {
                        'level': level_key,
                        'exit_pct': level['exit'],
                        'exit_qty': exit_qty,
                        'pnl_pct': pnl_pct,
                        'order': order
                    }
                    
                except Exception as e:
                    logger.error(f"Partial exit failed for {symbol}: {e}")
                    return None
        
        return None
    
    def should_set_breakeven(self, symbol: str) -> bool:
        """
        본전 SL 설정 여부 체크
        첫 부분 익절 후 설정
        """
        if symbol not in self.exit_states:
            return False
        
        state = self.exit_states[symbol]
        
        # 첫 레벨 완료 && 아직 본전 설정 안됨
        return (
            len(state['levels_completed']) > 0 and
            not state['breakeven_set']
        )
    
    def mark_breakeven_set(self, symbol: str):
        """본전 SL 설정 완료 표시"""
        if symbol in self.exit_states:
            self.exit_states[symbol]['breakeven_set'] = True
    
    def get_exit_stats(self, symbol: str) -> Dict:
        """익절 통계"""
        if symbol not in self.exit_states:
            return {}
        
        state = self.exit_states[symbol]
        levels_count = 3 if state['mode'] == "SCALP" else 4
        
        return {
            'mode': state['mode'],
            'completed_levels': len(state['levels_completed']),
            'total_levels': levels_count,
            'breakeven_set': state['breakeven_set'],
            'first_exit_time': state['first_exit_time']
        }
