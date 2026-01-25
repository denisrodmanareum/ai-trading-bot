# 💰 잔고 기반 동적 전략 분석 (100 USDT 시작)

## 📊 **현재 시스템 분석 (100 USDT 계정)**

### **현재 설정:**
```python
# 포지션 사이징
core_coin_ratio = 0.05  # 5%
alt_coin_ratio = 0.02   # 2%

# 레버리지
core_max = 20x
alt_max = 5x
```

### **100 USDT 계정 시뮬레이션:**

#### **시나리오 1: BTC (코어코인)**
```
포지션 크기: 100 × 5% = 5 USDT
레버리지: 20x (AI 확신도 90%+)
실제 거래 규모: 5 × 20 = 100 USDT
수익 3%: 100 × 3% = 3 USDT
수수료: 100 × 0.04% × 2 = 0.08 USDT
순수익: 3 - 0.08 = 2.92 USDT (2.92%)
```

#### **시나리오 2: DOGE (알트코인)**
```
포지션 크기: 100 × 2% = 2 USDT
레버리지: 5x
실제 거래 규모: 2 × 5 = 10 USDT
수익 3%: 10 × 3% = 0.3 USDT
수수료: 10 × 0.04% × 2 = 0.008 USDT
순수익: 0.3 - 0.008 = 0.292 USDT (0.29%)
```

### **문제점:**
1. ❌ **알트코인 수익 너무 작음** (0.29 USDT per trade)
2. ❌ **성장 속도 느림** (10회 성공 = +29 USDT)
3. ❌ **심리적 압박** (100불이 110불 되는데 30회 승리 필요)
4. ❌ **최소 거래 단위 문제** (거래소 min notional 제한)

---

## 🎯 **100 USDT 계정 최적 전략**

### **전략 A: 공격적 성장 (빠른 복리 증식)**

#### **목표:** 100 → 500 USDT (5배) → 1000 USDT (10배)

```python
# 잔고 티어 시스템
class BalanceTier:
    MICRO = (0, 200)      # 100-200 USDT: 초공격적
    SMALL = (200, 500)    # 200-500 USDT: 공격적
    MEDIUM = (500, 2000)  # 500-2K USDT: 균형
    LARGE = (2000, float('inf'))  # 2K+ USDT: 안정적

# Tier별 레버리지 및 포지션 크기
TIER_CONFIG = {
    "MICRO": {
        "core_ratio": 0.15,      # 15% (공격적!)
        "alt_ratio": 0.08,       # 8%
        "core_max_leverage": 20, # 코어에 집중
        "alt_max_leverage": 10,  # 알트도 기회 활용
        "min_position_usd": 10,  # 최소 10 USDT 거래
        "max_daily_trades": 8    # 기회 많이 잡기
    },
    "SMALL": {
        "core_ratio": 0.10,      # 10%
        "alt_ratio": 0.05,       # 5%
        "core_max_leverage": 15,
        "alt_max_leverage": 8,
        "min_position_usd": 15,
        "max_daily_trades": 6
    },
    "MEDIUM": {
        "core_ratio": 0.07,      # 7%
        "alt_ratio": 0.03,       # 3%
        "core_max_leverage": 12,
        "alt_max_leverage": 6,
        "min_position_usd": 20,
        "max_daily_trades": 5
    },
    "LARGE": {
        "core_ratio": 0.05,      # 5% (현재 설정)
        "alt_ratio": 0.02,       # 2%
        "core_max_leverage": 10,
        "alt_max_leverage": 5,
        "min_position_usd": 50,
        "max_daily_trades": 4
    }
}
```

#### **MICRO 티어 (100 USDT) 시뮬레이션:**

**BTC (코어코인):**
```
포지션 크기: 100 × 15% = 15 USDT
레버리지: 20x (AI 확신도 90%+)
실제 거래 규모: 15 × 20 = 300 USDT
수익 3%: 300 × 3% = 9 USDT
수수료: 300 × 0.04% × 2 = 0.24 USDT
순수익: 9 - 0.24 = 8.76 USDT (8.76%)
```

**DOGE (알트코인):**
```
포지션 크기: 100 × 8% = 8 USDT
레버리지: 10x (알트도 공격적)
실제 거래 규모: 8 × 10 = 80 USDT
수익 3%: 80 × 3% = 2.4 USDT
수수료: 80 × 0.04% × 2 = 0.064 USDT
순수익: 2.4 - 0.064 = 2.34 USDT (2.34%)
```

**개선 효과:**
- ✅ BTC 수익: 2.92 → **8.76 USDT (3배!)**
- ✅ DOGE 수익: 0.29 → **2.34 USDT (8배!)**
- ✅ 성장 속도: 10회 성공 = +87 USDT (거의 2배!)

---

### **전략 B: AI 기반 동적 레버리지**

#### **개념:**
```python
def calculate_dynamic_leverage(
    balance: float,
    ai_confidence: float,
    signal_strength: int,
    market_volatility: float,
    coin_type: str  # "CORE" or "ALT"
) -> int:
    """
    AI가 잔고, 확신도, 시장 상황을 종합해 최적 레버리지 계산
    """
    # 1. 잔고 티어 결정
    tier = get_balance_tier(balance)
    
    # 2. 기본 레버리지 (티어별)
    base_lev = TIER_CONFIG[tier][f"{coin_type.lower()}_max_leverage"]
    
    # 3. AI 확신도 가중치
    if ai_confidence >= 0.95:
        confidence_mult = 1.0  # 최대 레버리지 허용
    elif ai_confidence >= 0.85:
        confidence_mult = 0.8
    elif ai_confidence >= 0.75:
        confidence_mult = 0.6
    else:
        confidence_mult = 0.4  # 낮은 확신 = 낮은 레버리지
    
    # 4. 시장 변동성 조정
    if market_volatility > 0.05:  # 고변동성
        vol_mult = 0.7  # 레버리지 낮춤
    elif market_volatility > 0.03:
        vol_mult = 0.85
    else:
        vol_mult = 1.0  # 안정적
    
    # 5. 신호 강도 가중치
    signal_mult = {
        5: 1.0,   # 매우 강함
        4: 0.85,
        3: 0.7,
        2: 0.5,
        1: 0.3
    }.get(signal_strength, 0.5)
    
    # 6. 최종 레버리지 계산
    dynamic_lev = int(base_lev * confidence_mult * vol_mult * signal_mult)
    
    # 7. 안전 범위 제한
    min_lev = 3
    max_lev = base_lev
    
    return max(min_lev, min(dynamic_lev, max_lev))
```

#### **예시:**

**상황 1: 완벽한 조건 (100 USDT 계정, BTC)**
```python
balance = 100
ai_confidence = 0.96  # 매우 높음
signal_strength = 5
market_volatility = 0.02  # 안정적
coin_type = "CORE"

결과:
- 티어: MICRO (base_lev = 20x)
- 확신도: 0.96 → 1.0
- 변동성: 0.02 → 1.0
- 신호: 5 → 1.0
- 최종 레버리지: 20 × 1.0 × 1.0 × 1.0 = 20x ✅
```

**상황 2: 중간 조건 (100 USDT 계정, DOGE)**
```python
balance = 100
ai_confidence = 0.78  # 중간
signal_strength = 3
market_volatility = 0.04  # 보통
coin_type = "ALT"

결과:
- 티어: MICRO (base_lev = 10x)
- 확신도: 0.78 → 0.6
- 변동성: 0.04 → 0.85
- 신호: 3 → 0.7
- 최종 레버리지: 10 × 0.6 × 0.85 × 0.7 = 3.57 → 4x
```

**상황 3: 약한 조건 (100 USDT 계정)**
```python
balance = 100
ai_confidence = 0.68  # 낮음
signal_strength = 2
market_volatility = 0.06  # 고변동성
coin_type = "CORE"

결과:
- 티어: MICRO (base_lev = 20x)
- 확신도: 0.68 → 0.4
- 변동성: 0.06 → 0.7
- 신호: 2 → 0.5
- 최종 레버리지: 20 × 0.4 × 0.7 × 0.5 = 2.8 → 3x (최소값)
```

---

### **전략 C: 동적 포지션 사이징**

#### **개념:**
```python
def calculate_dynamic_position_size(
    balance: float,
    ai_confidence: float,
    recent_winrate: float,  # 최근 10회 승률
    coin_type: str
) -> float:
    """
    AI가 잔고와 최근 성과를 보고 포지션 크기 조정
    """
    tier = get_balance_tier(balance)
    base_ratio = TIER_CONFIG[tier][f"{coin_type.lower()}_ratio"]
    
    # 1. AI 확신도 가중치 (기존)
    if ai_confidence >= 0.95:
        conf_weight = 1.5
    elif ai_confidence >= 0.85:
        conf_weight = 1.2
    elif ai_confidence >= 0.75:
        conf_weight = 1.0
    elif ai_confidence >= 0.60:
        conf_weight = 0.8
    else:
        conf_weight = 0.5
    
    # 2. 🔧 NEW: 최근 성과 기반 가중치
    if recent_winrate >= 0.70:  # 연승 중
        performance_weight = 1.3  # 포지션 증가
    elif recent_winrate >= 0.50:
        performance_weight = 1.0
    elif recent_winrate >= 0.30:
        performance_weight = 0.7  # 연패 중 - 축소
    else:
        performance_weight = 0.5  # 심각한 연패 - 크게 축소
    
    # 3. 최종 포지션 비율
    final_ratio = base_ratio * conf_weight * performance_weight
    
    # 4. 최소/최대 제한
    max_ratio = base_ratio * 2.0  # 최대 2배까지만
    min_ratio = base_ratio * 0.3  # 최소 30%
    
    final_ratio = max(min_ratio, min(final_ratio, max_ratio))
    
    # 5. 최소 거래 크기 보장
    position_size = balance * final_ratio
    min_position = TIER_CONFIG[tier]["min_position_usd"]
    
    if position_size < min_position:
        position_size = min_position
        logger.warning(f"Position size too small, using minimum: {min_position} USDT")
    
    return position_size
```

#### **예시 (100 USDT 계정):**

**상황 1: 연승 중 + 고확신**
```python
balance = 100
ai_confidence = 0.92
recent_winrate = 0.80  # 10회 중 8승
coin_type = "CORE"

결과:
- 기본 비율: 15% (MICRO 티어)
- 확신도: 0.92 → 1.2
- 성과: 0.80 → 1.3
- 최종: 15% × 1.2 × 1.3 = 23.4%
- 포지션: 100 × 23.4% = 23.4 USDT ✅ (공격적!)
```

**상황 2: 연패 중 + 낮은 확신**
```python
balance = 100
ai_confidence = 0.65
recent_winrate = 0.20  # 10회 중 2승 (위험!)
coin_type = "CORE"

결과:
- 기본 비율: 15%
- 확신도: 0.65 → 0.8
- 성과: 0.20 → 0.5
- 최종: 15% × 0.8 × 0.5 = 6%
- 포지션: 100 × 6% = 6 USDT
- 최소 보장: 10 USDT (MICRO 티어 최소값)
- 실제 포지션: 10 USDT ✅ (보수적!)
```

---

## 📈 **100 USDT → 1000 USDT 성장 시뮬레이션**

### **시나리오: 공격적 성장 전략**

**가정:**
- 승률: 50%
- 평균 수익: +4% (MICRO 티어 공격적 설정)
- 평균 손실: -1.5% (SL 타이트)
- 일 트레이드: 6회
- 월 트레이드: 180회

#### **월별 성장:**

**1개월차 (MICRO 티어):**
```
시작: 100 USDT
평균 수익/트레이드: (50% × 4%) + (50% × -1.5%) = 1.25%
월 수익: 100 × (1.0125)^180 = 1,075 USDT
```

**이론적 vs 현실적:**
- **이론적**: 10배 성장 가능
- **현실적**: Circuit Breaker, 손실 한도로 인해 **2~3배 성장**
- **예상 1개월 후**: **200~300 USDT** ✅

**2개월차 (SMALL 티어):**
```
시작: 250 USDT
티어 변경: MICRO → SMALL (레버리지 하향)
포지션 비율: 15% → 10%
예상 월 수익: 50~70%
2개월 후: 375~425 USDT
```

**3개월차 (MEDIUM 티어):**
```
시작: 400 USDT
티어 변경: SMALL → MEDIUM
포지션 비율: 10% → 7%
예상 월 수익: 30~40%
3개월 후: 520~600 USDT
```

**4-5개월차 (MEDIUM 티어):**
```
시작: 550 USDT
안정적 성장 단계
예상 월 수익: 25~30%
5개월 후: 850~1,000 USDT ✅
```

**결론: 100 → 1000 USDT = 5개월 (현실적)**

---

## ⚖️ **전략 비교**

### **A. 현재 전략 (고정 비율)**
```
100 USDT 계정:
- 포지션: 5 USDT (5%)
- 레버리지: 20x (코어)
- 거래 규모: 100 USDT
- 수익/트레이드: ~3 USDT
- 월 성장: 30~40%
- 100 → 1000: 8~10개월
```

### **B. MICRO 티어 전략 (권장!)**
```
100 USDT 계정:
- 포지션: 15 USDT (15%)
- 레버리지: 20x (코어)
- 거래 규모: 300 USDT
- 수익/트레이드: ~9 USDT
- 월 성장: 80~120%
- 100 → 1000: 4~6개월
```

### **C. AI 동적 전략 (최적!)**
```
100 USDT 계정:
- 포지션: 10~23 USDT (동적)
- 레버리지: 3~20x (상황별)
- 연승 시 공격적, 연패 시 보수적
- 월 성장: 60~100% (안전하게)
- 100 → 1000: 5~7개월
- 리스크 관리 우수 ✅
```

---

## 🛡️ **리스크 관리 (소액 계정)**

### **MICRO 티어 특별 규칙:**

```python
MICRO_TIER_SAFETY = {
    # 1. 일일 손실 한도 (잔고 대비)
    "max_daily_loss_pct": 0.15,  # 15% (100불 → 15불)
    
    # 2. 연속 손실 제한
    "max_consecutive_losses": 3,  # 3연패 시 트레이딩 중단
    
    # 3. 단일 포지션 최대 리스크
    "max_single_position_risk": 0.20,  # 20% (20불)
    
    # 4. Circuit Breaker (더 빠른 개입)
    "circuit_breaker_loss": 0.10,  # -10% (10불) 시 30분 정지
    
    # 5. 최소 잔고 유지
    "min_balance_to_trade": 50,  # 50불 미만 시 트레이딩 중단
    
    # 6. 복구 모드 (연패 후)
    "recovery_mode_after_losses": 3,
    "recovery_leverage_reduction": 0.5,  # 레버리지 50% 감소
    "recovery_position_reduction": 0.7   # 포지션 크기 30% 감소
}
```

### **복구 모드 예시:**

```python
# 정상 모드
balance = 100
position_size = 15 USDT (15%)
leverage = 20x

# 3연패 후 복구 모드 진입
balance = 91 (3회 × -3 USDT 손실)
position_size = 15 × 0.7 = 10.5 USDT
leverage = 20 × 0.5 = 10x
→ 거래 규모: 105 USDT (더 보수적)

# 2연승 시 복구 모드 해제
balance = 97
정상 모드 복귀
```

---

## 🎯 **최종 권장사항 (100 USDT 시작)**

### **즉시 적용 (Critical):**

```python
# 1. 잔고 티어 시스템 도입
def get_balance_tier(balance: float) -> str:
    if balance < 200:
        return "MICRO"
    elif balance < 500:
        return "SMALL"
    elif balance < 2000:
        return "MEDIUM"
    else:
        return "LARGE"

# 2. MICRO 티어 설정 (100 USDT 최적화)
MICRO_CONFIG = {
    "core_ratio": 0.15,          # 15% (현재 5%에서 상향)
    "alt_ratio": 0.08,           # 8% (현재 2%에서 상향)
    "core_max_leverage": 20,     # 유지
    "alt_max_leverage": 10,      # 5x → 10x (알트 기회 활용)
    "min_position_usd": 10,      # 최소 거래 크기 보장
}

# 3. AI 동적 레버리지 활성화
use_dynamic_leverage = True
leverage_factors = ["ai_confidence", "volatility", "signal_strength"]

# 4. 성과 기반 포지션 사이징 활성화
use_performance_based_sizing = True
lookback_trades = 10  # 최근 10회 성과 추적
```

### **1주 내 적용 (Important):**

1. **백테스트 MICRO 티어 전략** (100~200 USDT 구간)
2. **복구 모드 테스트** (3연패 시나리오)
3. **최소 거래 크기 검증** (거래소 min notional)
4. **일일 손실 한도 조정** (15% 적절한지 확인)

### **1개월 내 적용 (Enhancement):**

1. **티어 자동 전환 시스템**
2. **실시간 성과 추적 대시보드**
3. **잔고별 최적 전략 A/B 테스트**
4. **복리 계산기 UI 추가** (100 → 1000 시뮬레이션)

---

## 💡 **코드 구현 예시**

```python
# auto_trading.py에 추가
class BalanceBasedStrategyManager:
    def __init__(self):
        self.tier_configs = {
            "MICRO": {
                "min_balance": 0,
                "max_balance": 200,
                "core_ratio": 0.15,
                "alt_ratio": 0.08,
                "core_max_lev": 20,
                "alt_max_lev": 10,
                "max_daily_loss_pct": 0.15,
                "max_consecutive_losses": 3
            },
            "SMALL": {
                "min_balance": 200,
                "max_balance": 500,
                "core_ratio": 0.10,
                "alt_ratio": 0.05,
                "core_max_lev": 15,
                "alt_max_lev": 8,
                "max_daily_loss_pct": 0.12,
                "max_consecutive_losses": 4
            },
            # ... MEDIUM, LARGE
        }
        
        self.recent_trades = []  # 최근 10회 결과 추적
        self.recovery_mode = False
    
    def get_current_tier(self, balance: float) -> dict:
        for tier_name, config in self.tier_configs.items():
            if config["min_balance"] <= balance < config["max_balance"]:
                return {**config, "tier_name": tier_name}
        return self.tier_configs["LARGE"]
    
    def calculate_dynamic_leverage(
        self, 
        balance: float, 
        ai_confidence: float,
        signal_strength: int,
        market_volatility: float,
        is_core: bool
    ) -> int:
        tier = self.get_current_tier(balance)
        base_lev = tier["core_max_lev"] if is_core else tier["alt_max_lev"]
        
        # AI 확신도 가중치
        if ai_confidence >= 0.95:
            conf_mult = 1.0
        elif ai_confidence >= 0.85:
            conf_mult = 0.8
        elif ai_confidence >= 0.75:
            conf_mult = 0.6
        else:
            conf_mult = 0.4
        
        # 변동성 조정
        vol_mult = 0.7 if market_volatility > 0.05 else 1.0
        
        # 신호 강도
        signal_mult = {5: 1.0, 4: 0.85, 3: 0.7, 2: 0.5, 1: 0.3}.get(signal_strength, 0.5)
        
        # 복구 모드 체크
        recovery_mult = 0.5 if self.recovery_mode else 1.0
        
        dynamic_lev = int(base_lev * conf_mult * vol_mult * signal_mult * recovery_mult)
        return max(3, min(dynamic_lev, base_lev))
    
    def calculate_dynamic_position_size(
        self, 
        balance: float,
        ai_confidence: float,
        is_core: bool
    ) -> float:
        tier = self.get_current_tier(balance)
        base_ratio = tier["core_ratio"] if is_core else tier["alt_ratio"]
        
        # AI 가중치
        if ai_confidence >= 0.95:
            conf_weight = 1.5
        elif ai_confidence >= 0.85:
            conf_weight = 1.2
        elif ai_confidence >= 0.75:
            conf_weight = 1.0
        else:
            conf_weight = 0.7
        
        # 최근 성과 가중치
        recent_winrate = self.get_recent_winrate()
        if recent_winrate >= 0.70:
            perf_weight = 1.3
        elif recent_winrate >= 0.50:
            perf_weight = 1.0
        elif recent_winrate >= 0.30:
            perf_weight = 0.7
        else:
            perf_weight = 0.5
        
        # 복구 모드
        recovery_weight = 0.7 if self.recovery_mode else 1.0
        
        final_ratio = base_ratio * conf_weight * perf_weight * recovery_weight
        final_ratio = max(base_ratio * 0.3, min(final_ratio, base_ratio * 2.0))
        
        position_size = balance * final_ratio
        
        # 최소 거래 크기 보장
        min_position = 10 if tier["tier_name"] == "MICRO" else 20
        return max(position_size, min_position)
    
    def check_recovery_mode(self, balance: float):
        """3연패 시 복구 모드 진입"""
        if len(self.recent_trades) >= 3:
            last_three = self.recent_trades[-3:]
            if all(t['pnl'] < 0 for t in last_three):
                self.recovery_mode = True
                logger.warning(f"🚨 Recovery Mode Activated! Balance: {balance}")
            elif len([t for t in self.recent_trades[-5:] if t['pnl'] > 0]) >= 3:
                # 최근 5회 중 3승 시 복구 모드 해제
                self.recovery_mode = False
                logger.info(f"✅ Recovery Mode Deactivated! Balance: {balance}")
    
    def get_recent_winrate(self) -> float:
        if len(self.recent_trades) < 5:
            return 0.50  # 기본값
        recent = self.recent_trades[-10:]
        wins = len([t for t in recent if t['pnl'] > 0])
        return wins / len(recent)
```

---

## 📊 **요약**

### **100 USDT 계정 최적 설정:**

| 항목 | 현재 | 권장 (MICRO 티어) |
|-----|------|------------------|
| 코어 포지션 비율 | 5% | **15%** |
| 알트 포지션 비율 | 2% | **8%** |
| 코어 최대 레버리지 | 20x | **20x** (유지) |
| 알트 최대 레버리지 | 5x | **10x** (상향) |
| AI 동적 조정 | 확신도만 | **확신도 + 성과 + 변동성** |
| 복구 모드 | 없음 | **3연패 시 자동 진입** |
| 최소 거래 크기 | 없음 | **10 USDT** |

### **기대 효과:**
- ✅ 트레이드당 수익: 3 USDT → **9 USDT (3배)**
- ✅ 월 성장률: 30% → **80~100%**
- ✅ 100 → 1000 달성: 8~10개월 → **5~6개월**
- ✅ 리스크 관리: 복구 모드로 연패 방지

**다음 단계: 코드 구현할까요?** 🚀
