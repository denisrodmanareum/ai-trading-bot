"""
Balance-Based Dynamic Strategy Manager
잔고 티어 시스템 및 AI 동적 레버리지/포지션 사이징
"""

from loguru import logger
from typing import Dict, List, Tuple
import time


class BalanceTier:
    """잔고 티어 정의"""
    MICRO = "MICRO"    # 0-200 USDT: 초공격적 (소액 계정 빠른 성장)
    SMALL = "SMALL"    # 200-500 USDT: 공격적
    MEDIUM = "MEDIUM"  # 500-2000 USDT: 균형
    LARGE = "LARGE"    # 2000+ USDT: 안정적


class BalanceBasedStrategyManager:
    """
    잔고 기반 동적 전략 관리자
    
    핵심 기능:
    1. 잔고 티어 자동 감지 및 전환
    2. AI 동적 레버리지 계산
    3. 성과 기반 포지션 사이징
    4. 복구 모드 (연패 시 보수적 전환)
    """
    
    def __init__(self):
        # 티어별 설정
        self.tier_configs = {
            BalanceTier.MICRO: {
                "min_balance": 0,
                "max_balance": 200,
                "core_ratio": 0.15,          # 15% (공격적!)
                "alt_ratio": 0.08,           # 8%
                "core_max_lev": 20,          # 코어에 집중
                "alt_max_lev": 10,           # 알트도 기회 활용
                "min_position_usd": 10,      # 최소 거래 크기
                "max_daily_trades": 8,       # 기회 많이 잡기
                "max_daily_loss_pct": 0.15,  # 15% 손실 한도
                "max_consecutive_losses": 3  # 3연패 제한
            },
            BalanceTier.SMALL: {
                "min_balance": 200,
                "max_balance": 500,
                "core_ratio": 0.10,          # 10%
                "alt_ratio": 0.05,           # 5%
                "core_max_lev": 15,
                "alt_max_lev": 8,
                "min_position_usd": 15,
                "max_daily_trades": 6,
                "max_daily_loss_pct": 0.12,
                "max_consecutive_losses": 4
            },
            BalanceTier.MEDIUM: {
                "min_balance": 500,
                "max_balance": 2000,
                "core_ratio": 0.07,          # 7%
                "alt_ratio": 0.03,           # 3%
                "core_max_lev": 12,
                "alt_max_lev": 6,
                "min_position_usd": 20,
                "max_daily_trades": 5,
                "max_daily_loss_pct": 0.10,
                "max_consecutive_losses": 4
            },
            BalanceTier.LARGE: {
                "min_balance": 2000,
                "max_balance": float('inf'),
                "core_ratio": 0.05,          # 5% (현재 설정)
                "alt_ratio": 0.02,           # 2%
                "core_max_lev": 10,
                "alt_max_lev": 5,
                "min_position_usd": 50,
                "max_daily_trades": 4,
                "max_daily_loss_pct": 0.08,
                "max_consecutive_losses": 5
            }
        }
        
        # 최근 트레이드 기록 (성과 추적용)
        self.recent_trades: List[Dict] = []
        self.max_trade_history = 20  # 최근 20개 기록
        
        # 복구 모드 상태
        self.recovery_mode = False
        self.recovery_start_time = None
        self.recovery_min_wins = 3  # 복구 해제 조건: 최근 5회 중 3승
        
        # 일일 통계
        self.daily_trade_count = 0
        self.daily_reset_time = time.time()
        
        logger.info("🎯 Balance-Based Strategy Manager Initialized")
    
    def get_current_tier(self, balance: float) -> Dict:
        """
        현재 잔고에 맞는 티어 설정 반환
        
        Args:
            balance: 현재 잔고 (USDT)
            
        Returns:
            티어 설정 딕셔너리
        """
        for tier_name, config in self.tier_configs.items():
            if config["min_balance"] <= balance < config["max_balance"]:
                result = {**config, "tier_name": tier_name}
                return result
        
        # 범위 초과 시 LARGE 반환
        return {**self.tier_configs[BalanceTier.LARGE], "tier_name": BalanceTier.LARGE}
    
    def calculate_dynamic_leverage(
        self,
        balance: float,
        ai_confidence: float,
        signal_strength: int,
        market_volatility: float,
        is_core: bool
    ) -> int:
        """
        AI 동적 레버리지 계산
        
        요소:
        1. 잔고 티어 (기본 레버리지)
        2. AI 확신도 (0.4~1.0 가중치)
        3. 시장 변동성 (0.7~1.0 가중치)
        4. 신호 강도 (0.3~1.0 가중치)
        5. 복구 모드 (0.5 페널티)
        
        Args:
            balance: 현재 잔고
            ai_confidence: AI 확신도 (0.0~1.0)
            signal_strength: 신호 강도 (1~5)
            market_volatility: 시장 변동성 (0.0~1.0)
            is_core: 코어 코인 여부
            
        Returns:
            최종 레버리지 (int)
        """
        tier = self.get_current_tier(balance)
        base_lev = tier["core_max_lev"] if is_core else tier["alt_max_lev"]
        
        # 1. AI 확신도 가중치
        if ai_confidence >= 0.95:
            conf_mult = 1.0      # 완벽한 확신
        elif ai_confidence >= 0.85:
            conf_mult = 0.8      # 강한 확신
        elif ai_confidence >= 0.75:
            conf_mult = 0.6      # 보통 확신
        elif ai_confidence >= 0.65:
            conf_mult = 0.5      # 약한 확신
        else:
            conf_mult = 0.4      # 매우 약한 확신
        
        # 2. 변동성 조정
        if market_volatility > 0.05:    # 고변동성 (5% 이상)
            vol_mult = 0.7               # 레버리지 30% 감소
        elif market_volatility > 0.03:  # 중간 변동성
            vol_mult = 0.85
        else:
            vol_mult = 1.0               # 안정적
        
        # 3. 신호 강도 가중치
        signal_multipliers = {
            5: 1.0,   # 매우 강함
            4: 0.85,  # 강함
            3: 0.7,   # 중간
            2: 0.5,   # 약함
            1: 0.3    # 매우 약함
        }
        signal_mult = signal_multipliers.get(signal_strength, 0.5)
        
        # 4. 복구 모드 체크
        recovery_mult = 0.5 if self.recovery_mode else 1.0
        
        # 5. 최종 레버리지 계산
        dynamic_lev = int(base_lev * conf_mult * vol_mult * signal_mult * recovery_mult)
        
        # 6. 안전 범위 제한
        min_lev = 3   # 최소 3x
        max_lev = base_lev
        
        final_lev = max(min_lev, min(dynamic_lev, max_lev))
        
        logger.debug(
            f"🎲 Dynamic Leverage: {final_lev}x "
            f"(Base: {base_lev}x, Conf: {conf_mult:.1f}, Vol: {vol_mult:.1f}, "
            f"Signal: {signal_mult:.1f}, Recovery: {recovery_mult:.1f})"
        )
        
        return final_lev
    
    def calculate_dynamic_position_size(
        self,
        balance: float,
        ai_confidence: float,
        is_core: bool,
        is_btc_only: bool = False
    ) -> float:
        """
        동적 포지션 사이징 계산
        
        요소:
        1. 잔고 티어 (기본 비율)
        2. AI 확신도 (0.5~1.5 가중치)
        3. 최근 성과 (0.5~1.3 가중치)
        4. 복구 모드 (0.7 페널티)
        5. BTC Only 모드 (3.0배 가중치 - 집중 투자)
        
        Args:
            balance: 현재 잔고
            ai_confidence: AI 확신도
            is_core: 코어 코인 여부
            is_btc_only: BTC Only 모드 여부 (True일 경우 비중 대폭 확대)
            
        Returns:
            포지션 크기 (USDT)
        """
        tier = self.get_current_tier(balance)
        
        # 0. BTC Only 가중치 (집중 투자: 33% 고정)
        if is_btc_only:
            base_ratio = 0.33
            max_ratio_limit = 0.50
            min_ratio_limit = 0.15
            logger.debug(f"₿ BTC Only Mode: Setting base ratio to 33%")
        else:
            base_ratio = tier["core_ratio"] if is_core else tier["alt_ratio"]
            max_ratio_limit = base_ratio * 2.0
            min_ratio_limit = base_ratio * 0.3
        
        # 1. AI 확신도 가중치
        if ai_confidence >= 0.95:
            conf_weight = 1.5      # 초강력 확신: 1.5배
        elif ai_confidence >= 0.85:
            conf_weight = 1.3      # 강력 확신: 1.3배
        elif ai_confidence >= 0.75:
            conf_weight = 1.0      # 보통
        elif ai_confidence >= 0.60:
            conf_weight = 0.8      # 약함
        else:
            conf_weight = 0.5      # 매우 약함
        
        # 2. 최근 성과 가중치
        recent_winrate = self.get_recent_winrate()
        if recent_winrate >= 0.70:      # 70% 이상 승률 (연승 중)
            perf_weight = 1.3           # 포지션 증가
        elif recent_winrate >= 0.50:
            perf_weight = 1.0           # 유지
        elif recent_winrate >= 0.30:
            perf_weight = 0.7           # 축소
        else:                           # 30% 미만 (심각한 연패)
            perf_weight = 0.5           # 크게 축소
        
        # 3. 복구 모드 페널티
        recovery_weight = 0.7 if self.recovery_mode else 1.0
        
        # 4. 최종 비율 계산
        final_ratio = base_ratio * conf_weight * perf_weight * recovery_weight
        
        # 5. 최소/최대 제한
        final_ratio = max(min_ratio_limit, min(final_ratio, max_ratio_limit))
        
        # 6. 포지션 크기 계산
        position_size = balance * final_ratio
        
        # 7. 최소 거래 크기 보장
        min_position = tier["min_position_usd"]
        if position_size < min_position:
            position_size = min_position
            logger.warning(
                f"⚠️ Position too small ({balance * final_ratio:.1f} USDT), "
                f"using minimum: {min_position} USDT"
            )
        
        logger.debug(
            f"💰 Dynamic Position: {position_size:.1f} USDT "
            f"(Ratio: {final_ratio*100:.1f}%, Conf: {conf_weight:.1f}, "
            f"Perf: {perf_weight:.1f}, Recovery: {recovery_weight:.1f})"
        )
        
        return position_size
    
    def add_trade_result(self, symbol: str, pnl: float, win: bool):
        """
        트레이드 결과 기록
        
        Args:
            symbol: 거래 심볼
            pnl: 손익 (USDT)
            win: 승리 여부
        """
        trade_result = {
            "timestamp": time.time(),
            "symbol": symbol,
            "pnl": pnl,
            "win": win
        }
        
        self.recent_trades.append(trade_result)
        
        # 최대 기록 수 유지
        if len(self.recent_trades) > self.max_trade_history:
            self.recent_trades.pop(0)
        
        # 일일 카운트 증가
        self.daily_trade_count += 1
        
        # 복구 모드 체크
        self.check_recovery_mode()
        
        logger.debug(
            f"📊 Trade Recorded: {symbol} | "
            f"{'✅ WIN' if win else '❌ LOSS'} | PnL: {pnl:+.2f} USDT"
        )
    
    def get_recent_winrate(self, lookback: int = 10) -> float:
        """
        최근 승률 계산
        
        Args:
            lookback: 조회할 트레이드 수
            
        Returns:
            승률 (0.0~1.0)
        """
        if len(self.recent_trades) < 5:
            return 0.50  # 기본값 (데이터 부족)
        
        recent = self.recent_trades[-lookback:]
        wins = len([t for t in recent if t['win']])
        winrate = wins / len(recent)
        
        return winrate
    
    def check_recovery_mode(self):
        """
        복구 모드 체크 및 전환
        
        조건:
        - 진입: 3연패
        - 해제: 최근 5회 중 3승
        """
        if len(self.recent_trades) < 3:
            return
        
        # 3연패 체크 (복구 모드 진입)
        last_three = self.recent_trades[-3:]
        if all(not t['win'] for t in last_three):
            if not self.recovery_mode:
                self.recovery_mode = True
                self.recovery_start_time = time.time()
                logger.warning(
                    "🚨 RECOVERY MODE ACTIVATED! "
                    "3 consecutive losses detected. Trading conservatively."
                )
        
        # 복구 조건 체크 (복구 모드 해제)
        elif self.recovery_mode and len(self.recent_trades) >= 5:
            last_five = self.recent_trades[-5:]
            wins = len([t for t in last_five if t['win']])
            
            if wins >= self.recovery_min_wins:
                recovery_duration = time.time() - self.recovery_start_time
                self.recovery_mode = False
                self.recovery_start_time = None
                logger.info(
                    f"✅ RECOVERY MODE DEACTIVATED! "
                    f"Performance restored ({wins}/5 wins, duration: {recovery_duration/60:.1f} min)"
                )
    
    def check_daily_trade_limit(self, balance: float) -> Tuple[bool, str]:
        """
        일일 트레이드 제한 체크
        
        Args:
            balance: 현재 잔고
            
        Returns:
            (허용 여부, 메시지)
        """
        # 일일 리셋 체크 (24시간마다)
        if time.time() - self.daily_reset_time > 86400:
            self.daily_trade_count = 0
            self.daily_reset_time = time.time()
            logger.info("🔄 Daily trade counter reset")
        
        tier = self.get_current_tier(balance)
        max_trades = tier["max_daily_trades"]
        
        if self.daily_trade_count >= max_trades:
            return False, f"Daily trade limit reached ({max_trades} trades)"
        
        return True, "OK"
    
    def get_tier_info(self, balance: float) -> Dict:
        """
        현재 티어 정보 반환 (UI용)
        
        Args:
            balance: 현재 잔고
            
        Returns:
            티어 정보 딕셔너리
        """
        tier = self.get_current_tier(balance)
        recent_winrate = self.get_recent_winrate()
        
        return {
            "tier_name": tier["tier_name"],
            "balance_range": f"{tier['min_balance']}-{tier['max_balance']} USDT",
            "core_ratio": f"{tier['core_ratio']*100:.0f}%",
            "alt_ratio": f"{tier['alt_ratio']*100:.0f}%",
            "core_max_leverage": f"{tier['core_max_lev']}x",
            "alt_max_leverage": f"{tier['alt_max_lev']}x",
            "min_position": f"{tier['min_position_usd']} USDT",
            "max_daily_trades": tier["max_daily_trades"],
            "daily_trade_count": self.daily_trade_count,
            "recent_winrate": f"{recent_winrate*100:.1f}%",
            "recovery_mode": self.recovery_mode,
            "recent_trades_count": len(self.recent_trades)
        }
    
    def reset_stats(self):
        """통계 초기화"""
        self.recent_trades.clear()
        self.recovery_mode = False
        self.recovery_start_time = None
        self.daily_trade_count = 0
        self.daily_reset_time = time.time()
        logger.info("🔄 Strategy Manager Stats Reset")
