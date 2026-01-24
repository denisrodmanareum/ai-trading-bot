"""
Smart Money Concept (SMC) Trading Strategy
스마트 머니 컨셉 트레이딩 전략

주요 개념:
1. BOS (Break of Structure) - 구조 돌파
2. Order Block (OB) - 기관 주문 블록
3. Fair Value Gap (FVG) - 공정 가치 갭
4. Market Structure - 시장 구조 (HH, HL, LH, LL)
5. Retest - 되돌림 테스트
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from loguru import logger
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SwingPoint:
    """스윙 고점/저점"""
    index: int
    price: float
    type: str  # 'HIGH' or 'LOW'
    timestamp: datetime
    confirmed: bool = False


@dataclass
class OrderBlock:
    """오더블록 (기관 주문 블록)"""
    start_index: int
    end_index: int
    top: float  # 블록 상단
    bottom: float  # 블록 하단
    type: str  # 'BULLISH' or 'BEARISH'
    strength: int  # 1-5 (강도)
    volume: float
    tested: bool = False
    test_count: int = 0
    created_at: datetime
    
    def is_active(self, current_price: float) -> bool:
        """오더블록이 아직 활성 상태인지 확인"""
        if self.type == 'BULLISH':
            # 상승 OB: 가격이 블록 하단 아래로 떨어지면 비활성화
            return current_price >= self.bottom * 0.95
        else:
            # 하락 OB: 가격이 블록 상단 위로 올라가면 비활성화
            return current_price <= self.top * 1.05
    
    def is_in_zone(self, price: float, tolerance: float = 0.01) -> bool:
        """가격이 오더블록 존 안에 있는지 확인"""
        return self.bottom * (1 - tolerance) <= price <= self.top * (1 + tolerance)


@dataclass
class FairValueGap:
    """공정 가치 갭 (FVG) - 캔들 사이의 갭"""
    index: int
    top: float
    bottom: float
    type: str  # 'BULLISH' or 'BEARISH'
    filled: bool = False
    created_at: datetime
    
    def is_filled(self, current_price: float) -> bool:
        """갭이 채워졌는지 확인"""
        if self.type == 'BULLISH':
            # 상승 FVG: 가격이 하단까지 내려오면 채워짐
            return current_price <= self.bottom
        else:
            # 하락 FVG: 가격이 상단까지 올라가면 채워짐
            return current_price >= self.top


@dataclass
class BreakOfStructure:
    """구조 돌파 (BOS)"""
    index: int
    price: float
    type: str  # 'BULLISH_BOS' or 'BEARISH_BOS'
    previous_high: float
    previous_low: float
    strength: int  # 1-5
    confirmed: bool = False
    timestamp: datetime


class MarketStructure:
    """시장 구조 추적"""
    def __init__(self):
        self.swing_highs: List[SwingPoint] = []
        self.swing_lows: List[SwingPoint] = []
        self.current_trend = "UNKNOWN"  # UP, DOWN, RANGING
        self.last_higher_high: Optional[SwingPoint] = None
        self.last_lower_low: Optional[SwingPoint] = None
    
    def update_trend(self):
        """스윙 포인트 기반 트렌드 업데이트"""
        if not self.swing_highs or not self.swing_lows:
            self.current_trend = "UNKNOWN"
            return
        
        recent_highs = self.swing_highs[-3:] if len(self.swing_highs) >= 3 else self.swing_highs
        recent_lows = self.swing_lows[-3:] if len(self.swing_lows) >= 3 else self.swing_lows
        
        # Higher Highs & Higher Lows = Uptrend
        if len(recent_highs) >= 2:
            hh = all(recent_highs[i].price > recent_highs[i-1].price for i in range(1, len(recent_highs)))
        else:
            hh = False
        
        if len(recent_lows) >= 2:
            hl = all(recent_lows[i].price > recent_lows[i-1].price for i in range(1, len(recent_lows)))
        else:
            hl = False
        
        # Lower Lows & Lower Highs = Downtrend
        if len(recent_lows) >= 2:
            ll = all(recent_lows[i].price < recent_lows[i-1].price for i in range(1, len(recent_lows)))
        else:
            ll = False
        
        if len(recent_highs) >= 2:
            lh = all(recent_highs[i].price < recent_highs[i-1].price for i in range(1, len(recent_highs)))
        else:
            lh = False
        
        if hh and hl:
            self.current_trend = "UP"
        elif ll and lh:
            self.current_trend = "DOWN"
        else:
            self.current_trend = "RANGING"


class SmartMoneyConceptAnalyzer:
    """
    스마트 머니 컨셉 분석기
    
    기능:
    1. 고TF BOS 탐지
    2. 오더블럭 생성 및 추적
    3. OB 리테스트 확인
    4. FVG 탐지
    5. 하위TF 트리거 신호
    """
    
    def __init__(self, 
                 swing_lookback: int = 5,
                 ob_min_volume_percentile: float = 70,
                 fvg_min_size_pct: float = 0.5):
        """
        Args:
            swing_lookback: 스윙 포인트 탐지 시 좌우 확인 캔들 수
            ob_min_volume_percentile: OB 생성 최소 볼륨 백분위수
            fvg_min_size_pct: FVG 최소 크기 (가격 대비 %)
        """
        self.swing_lookback = swing_lookback
        self.ob_min_volume_percentile = ob_min_volume_percentile
        self.fvg_min_size_pct = fvg_min_size_pct
        
        # 상태 추적
        self.market_structure = MarketStructure()
        self.order_blocks: List[OrderBlock] = []
        self.fair_value_gaps: List[FairValueGap] = []
        self.bos_events: List[BreakOfStructure] = []
        
        # 최대 추적 개수
        self.max_order_blocks = 10
        self.max_fvgs = 5
        self.max_bos = 5
    
    def analyze(self, df_high: pd.DataFrame, df_low: pd.DataFrame) -> Dict:
        """
        멀티 타임프레임 SMC 분석
        
        Args:
            df_high: 고차 타임프레임 데이터 (예: 1h, 4h)
            df_low: 하위 타임프레임 데이터 (예: 15m, 5m)
        
        Returns:
            {
                'high_tf_bos': BreakOfStructure | None,
                'active_order_blocks': List[OrderBlock],
                'ob_retest_signal': Dict | None,
                'low_tf_trigger': Dict | None,
                'entry_signal': Dict | None
            }
        """
        result = {
            'high_tf_bos': None,
            'active_order_blocks': [],
            'ob_retest_signal': None,
            'low_tf_trigger': None,
            'entry_signal': None,
            'market_structure': None
        }
        
        try:
            # 1. 고TF 분석: BOS 탐지
            high_tf_bos = self._detect_bos(df_high)
            result['high_tf_bos'] = high_tf_bos
            
            # 2. 오더블록 생성 (고TF에서)
            if high_tf_bos and high_tf_bos.confirmed:
                self._create_order_blocks(df_high, high_tf_bos)
            
            # 3. 활성 오더블록 필터링
            current_price = float(df_low.iloc[-1]['close'])
            active_obs = self._get_active_order_blocks(current_price)
            result['active_order_blocks'] = active_obs
            
            # 4. OB 리테스트 확인 (하위TF에서)
            if active_obs:
                retest_signal = self._check_ob_retest(df_low, active_obs)
                result['ob_retest_signal'] = retest_signal
            
            # 5. FVG 탐지 (하위TF에서)
            self._detect_fair_value_gaps(df_low)
            
            # 6. 하위TF 트리거 신호
            if result['ob_retest_signal']:
                trigger = self._get_low_tf_trigger(df_low, result['ob_retest_signal'])
                result['low_tf_trigger'] = trigger
                
                # 7. 진입 신호 생성
                if trigger and trigger['valid']:
                    entry = self._generate_entry_signal(
                        df_low,
                        high_tf_bos,
                        result['ob_retest_signal'],
                        trigger
                    )
                    result['entry_signal'] = entry
            
            # 8. 시장 구조 정보
            result['market_structure'] = {
                'trend': self.market_structure.current_trend,
                'swing_highs_count': len(self.market_structure.swing_highs),
                'swing_lows_count': len(self.market_structure.swing_lows)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"SMC 분석 실패: {e}")
            return result
    
    def _detect_swing_points(self, df: pd.DataFrame) -> Tuple[List[SwingPoint], List[SwingPoint]]:
        """스윙 고점/저점 탐지"""
        highs = []
        lows = []
        
        lookback = self.swing_lookback
        
        for i in range(lookback, len(df) - lookback):
            # 스윙 고점: 좌우 lookback 캔들보다 높음
            is_swing_high = all(
                df.iloc[i]['high'] > df.iloc[j]['high']
                for j in range(i - lookback, i + lookback + 1)
                if j != i
            )
            
            if is_swing_high:
                highs.append(SwingPoint(
                    index=i,
                    price=float(df.iloc[i]['high']),
                    type='HIGH',
                    timestamp=df.iloc[i]['timestamp'] if 'timestamp' in df.columns else datetime.now(),
                    confirmed=True
                ))
            
            # 스윙 저점: 좌우 lookback 캔들보다 낮음
            is_swing_low = all(
                df.iloc[i]['low'] < df.iloc[j]['low']
                for j in range(i - lookback, i + lookback + 1)
                if j != i
            )
            
            if is_swing_low:
                lows.append(SwingPoint(
                    index=i,
                    price=float(df.iloc[i]['low']),
                    type='LOW',
                    timestamp=df.iloc[i]['timestamp'] if 'timestamp' in df.columns else datetime.now(),
                    confirmed=True
                ))
        
        return highs, lows
    
    def _detect_bos(self, df: pd.DataFrame) -> Optional[BreakOfStructure]:
        """고TF에서 BOS(Break of Structure) 탐지"""
        try:
            # 스윙 포인트 업데이트
            highs, lows = self._detect_swing_points(df)
            self.market_structure.swing_highs = highs
            self.market_structure.swing_lows = lows
            self.market_structure.update_trend()
            
            if len(highs) < 2 or len(lows) < 2:
                return None
            
            current_price = float(df.iloc[-1]['close'])
            current_index = len(df) - 1
            
            # 상승 BOS: 최근 고점 돌파
            recent_high = highs[-1].price
            prev_high = highs[-2].price if len(highs) >= 2 else recent_high
            
            if current_price > recent_high * 1.001:  # 0.1% 여유
                strength = self._calculate_bos_strength(df, 'BULLISH', current_price, recent_high)
                return BreakOfStructure(
                    index=current_index,
                    price=current_price,
                    type='BULLISH_BOS',
                    previous_high=recent_high,
                    previous_low=lows[-1].price if lows else 0,
                    strength=strength,
                    confirmed=True,
                    timestamp=datetime.now()
                )
            
            # 하락 BOS: 최근 저점 돌파
            recent_low = lows[-1].price
            prev_low = lows[-2].price if len(lows) >= 2 else recent_low
            
            if current_price < recent_low * 0.999:  # 0.1% 여유
                strength = self._calculate_bos_strength(df, 'BEARISH', current_price, recent_low)
                return BreakOfStructure(
                    index=current_index,
                    price=current_price,
                    type='BEARISH_BOS',
                    previous_high=highs[-1].price if highs else 0,
                    previous_low=recent_low,
                    strength=strength,
                    confirmed=True,
                    timestamp=datetime.now()
                )
            
            return None
            
        except Exception as e:
            logger.error(f"BOS 탐지 실패: {e}")
            return None
    
    def _calculate_bos_strength(self, df: pd.DataFrame, bos_type: str, current: float, broken_level: float) -> int:
        """BOS 강도 계산 (1-5)"""
        try:
            # 돌파 크기
            break_pct = abs(current - broken_level) / broken_level * 100
            
            # 볼륨
            recent_volume = float(df.iloc[-1]['volume'])
            avg_volume = float(df['volume'].tail(20).mean())
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
            
            # 강도 계산
            strength = 1
            
            if break_pct > 0.5:
                strength += 1
            if break_pct > 1.0:
                strength += 1
            if volume_ratio > 1.5:
                strength += 1
            if volume_ratio > 2.0:
                strength += 1
            
            return min(strength, 5)
            
        except Exception:
            return 1
    
    def _create_order_blocks(self, df: pd.DataFrame, bos: BreakOfStructure):
        """BOS 발생 직전의 캔들을 오더블록으로 생성"""
        try:
            if bos.index < 3:
                return
            
            # BOS 직전 1-3개 캔들 확인
            for lookback in range(1, 4):
                idx = bos.index - lookback
                if idx < 0:
                    continue
                
                candle = df.iloc[idx]
                volume = float(candle['volume'])
                
                # 볼륨 필터
                volume_threshold = df['volume'].quantile(self.ob_min_volume_percentile / 100)
                if volume < volume_threshold:
                    continue
                
                # 오더블록 생성
                ob_type = 'BULLISH' if bos.type == 'BULLISH_BOS' else 'BEARISH'
                
                ob = OrderBlock(
                    start_index=idx,
                    end_index=idx,
                    top=float(candle['high']),
                    bottom=float(candle['low']),
                    type=ob_type,
                    strength=bos.strength,
                    volume=volume,
                    created_at=datetime.now()
                )
                
                # 기존 OB와 겹치는지 확인
                is_duplicate = any(
                    abs(ob.top - existing.top) / ob.top < 0.01 and
                    abs(ob.bottom - existing.bottom) / ob.bottom < 0.01
                    for existing in self.order_blocks
                )
                
                if not is_duplicate:
                    self.order_blocks.append(ob)
                    logger.info(f"📦 {ob_type} 오더블록 생성: {ob.bottom:.2f} - {ob.top:.2f}")
            
            # 오래된 OB 제거
            self._cleanup_order_blocks()
            
        except Exception as e:
            logger.error(f"오더블록 생성 실패: {e}")
    
    def _get_active_order_blocks(self, current_price: float) -> List[OrderBlock]:
        """활성 오더블록 필터링"""
        active = [ob for ob in self.order_blocks if ob.is_active(current_price)]
        
        # 강도 순으로 정렬
        active.sort(key=lambda x: x.strength, reverse=True)
        
        return active[:self.max_order_blocks]
    
    def _check_ob_retest(self, df: pd.DataFrame, active_obs: List[OrderBlock]) -> Optional[Dict]:
        """오더블록 리테스트 확인"""
        try:
            current_price = float(df.iloc[-1]['close'])
            current_low = float(df.iloc[-1]['low'])
            current_high = float(df.iloc[-1]['high'])
            
            for ob in active_obs:
                # 가격이 OB 존에 진입했는지 확인
                in_zone = ob.is_in_zone(current_price, tolerance=0.02)
                
                # 하락 후 OB 터치 (상승 OB의 경우)
                if ob.type == 'BULLISH' and current_low <= ob.top and current_low >= ob.bottom:
                    ob.tested = True
                    ob.test_count += 1
                    
                    return {
                        'order_block': ob,
                        'type': 'BULLISH_RETEST',
                        'price': current_price,
                        'strength': ob.strength,
                        'test_count': ob.test_count,
                        'valid': ob.test_count <= 3  # 3번까지만 유효
                    }
                
                # 상승 후 OB 터치 (하락 OB의 경우)
                if ob.type == 'BEARISH' and current_high >= ob.bottom and current_high <= ob.top:
                    ob.tested = True
                    ob.test_count += 1
                    
                    return {
                        'order_block': ob,
                        'type': 'BEARISH_RETEST',
                        'price': current_price,
                        'strength': ob.strength,
                        'test_count': ob.test_count,
                        'valid': ob.test_count <= 3
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"OB 리테스트 확인 실패: {e}")
            return None
    
    def _detect_fair_value_gaps(self, df: pd.DataFrame):
        """Fair Value Gap (FVG) 탐지"""
        try:
            if len(df) < 3:
                return
            
            for i in range(2, len(df)):
                candle_1 = df.iloc[i-2]
                candle_2 = df.iloc[i-1]
                candle_3 = df.iloc[i]
                
                # 상승 FVG: 캔들1 고가 < 캔들3 저가
                if candle_1['high'] < candle_3['low']:
                    gap_size = (candle_3['low'] - candle_1['high']) / candle_1['high'] * 100
                    
                    if gap_size >= self.fvg_min_size_pct:
                        fvg = FairValueGap(
                            index=i,
                            top=float(candle_3['low']),
                            bottom=float(candle_1['high']),
                            type='BULLISH',
                            created_at=datetime.now()
                        )
                        self.fair_value_gaps.append(fvg)
                        logger.debug(f"📊 상승 FVG 탐지: {fvg.bottom:.2f} - {fvg.top:.2f}")
                
                # 하락 FVG: 캔들1 저가 > 캔들3 고가
                if candle_1['low'] > candle_3['high']:
                    gap_size = (candle_1['low'] - candle_3['high']) / candle_3['high'] * 100
                    
                    if gap_size >= self.fvg_min_size_pct:
                        fvg = FairValueGap(
                            index=i,
                            top=float(candle_1['low']),
                            bottom=float(candle_3['high']),
                            type='BEARISH',
                            created_at=datetime.now()
                        )
                        self.fair_value_gaps.append(fvg)
                        logger.debug(f"📊 하락 FVG 탐지: {fvg.bottom:.2f} - {fvg.top:.2f}")
            
            # 오래된 FVG 제거
            self._cleanup_fvgs()
            
        except Exception as e:
            logger.error(f"FVG 탐지 실패: {e}")
    
    def _get_low_tf_trigger(self, df: pd.DataFrame, retest_signal: Dict) -> Optional[Dict]:
        """하위 타임프레임에서 트리거 신호 확인"""
        try:
            if not retest_signal or not retest_signal.get('valid'):
                return None
            
            ob = retest_signal['order_block']
            current_candle = df.iloc[-1]
            prev_candle = df.iloc[-2] if len(df) >= 2 else None
            
            # BULLISH 트리거: OB 리테스트 후 상승 반전
            if ob.type == 'BULLISH':
                # 이전 캔들이 하락, 현재 캔들이 상승 + OB 존 내
                if prev_candle is not None:
                    prev_bearish = prev_candle['close'] < prev_candle['open']
                    curr_bullish = current_candle['close'] > current_candle['open']
                    
                    if prev_bearish and curr_bullish and ob.is_in_zone(float(current_candle['close'])):
                        return {
                            'type': 'BULLISH_TRIGGER',
                            'valid': True,
                            'entry_price': float(current_candle['close']),
                            'stop_loss': ob.bottom * 0.998,  # OB 하단 약간 아래
                            'take_profit': float(current_candle['close']) * 1.015,  # 1.5% 목표
                            'confidence': min(ob.strength / 5.0, 1.0)
                        }
            
            # BEARISH 트리거: OB 리테스트 후 하락 반전
            elif ob.type == 'BEARISH':
                if prev_candle is not None:
                    prev_bullish = prev_candle['close'] > prev_candle['open']
                    curr_bearish = current_candle['close'] < current_candle['open']
                    
                    if prev_bullish and curr_bearish and ob.is_in_zone(float(current_candle['close'])):
                        return {
                            'type': 'BEARISH_TRIGGER',
                            'valid': True,
                            'entry_price': float(current_candle['close']),
                            'stop_loss': ob.top * 1.002,  # OB 상단 약간 위
                            'take_profit': float(current_candle['close']) * 0.985,  # -1.5% 목표
                            'confidence': min(ob.strength / 5.0, 1.0)
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"하위TF 트리거 확인 실패: {e}")
            return None
    
    def _generate_entry_signal(
        self,
        df: pd.DataFrame,
        bos: Optional[BreakOfStructure],
        retest_signal: Dict,
        trigger: Dict
    ) -> Optional[Dict]:
        """최종 진입 신호 생성"""
        try:
            if not trigger or not trigger.get('valid'):
                return None
            
            ob = retest_signal['order_block']
            
            # 추가 확인: 고TF BOS 방향과 트리거 방향 일치
            if bos:
                bos_bullish = bos.type == 'BULLISH_BOS'
                trigger_bullish = trigger['type'] == 'BULLISH_TRIGGER'
                
                if bos_bullish != trigger_bullish:
                    logger.warning("⚠️ 고TF BOS와 트리거 방향 불일치")
                    return None
            
            # 신호 생성
            signal = {
                'action': 1 if trigger['type'] == 'BULLISH_TRIGGER' else 2,  # 1=LONG, 2=SHORT
                'entry_price': trigger['entry_price'],
                'stop_loss': trigger['stop_loss'],
                'take_profit': trigger['take_profit'],
                'confidence': trigger['confidence'],
                'reason': f"SMC_{trigger['type']}_OB_RETEST",
                'order_block': {
                    'top': ob.top,
                    'bottom': ob.bottom,
                    'strength': ob.strength,
                    'type': ob.type
                },
                'bos': {
                    'type': bos.type if bos else None,
                    'strength': bos.strength if bos else 0
                } if bos else None,
                'market_structure': self.market_structure.current_trend
            }
            
            return signal
            
        except Exception as e:
            logger.error(f"진입 신호 생성 실패: {e}")
            return None
    
    def _cleanup_order_blocks(self):
        """오래되거나 무효한 오더블록 제거"""
        # 최근 것만 유지
        if len(self.order_blocks) > self.max_order_blocks:
            self.order_blocks = sorted(
                self.order_blocks,
                key=lambda x: x.created_at,
                reverse=True
            )[:self.max_order_blocks]
    
    def _cleanup_fvgs(self):
        """오래된 FVG 제거"""
        if len(self.fair_value_gaps) > self.max_fvgs:
            self.fair_value_gaps = sorted(
                self.fair_value_gaps,
                key=lambda x: x.created_at,
                reverse=True
            )[:self.max_fvgs]
    
    def get_status_summary(self) -> Dict:
        """현재 상태 요약"""
        return {
            'market_trend': self.market_structure.current_trend,
            'active_order_blocks': len([ob for ob in self.order_blocks if not ob.tested]),
            'tested_order_blocks': len([ob for ob in self.order_blocks if ob.tested]),
            'active_fvgs': len([fvg for fvg in self.fair_value_gaps if not fvg.filled]),
            'recent_bos': len(self.bos_events),
            'swing_highs': len(self.market_structure.swing_highs),
            'swing_lows': len(self.market_structure.swing_lows)
        }
