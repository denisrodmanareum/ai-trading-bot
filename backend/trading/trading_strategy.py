import pandas as pd
from trading.stochastic_triple import StochasticTriple
from ta.momentum import RSIIndicator

class StochasticTradingStrategy:
    """
    Stochastic Triple Trading Strategy
    """
    def __init__(self):
        self.oversold = 25
        self.overbought = 75
        self.rsi_oversold = 30
        self.rsi_overbought = 70

    def check_momentum(self, df: pd.DataFrame):
        """
        Check for rapid price moves (Pump/Dump)
        """
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 1. Volume Spike (2x average)
        vol_spike = latest['volume'] > (latest['volume_sma'] * 2.0)
        
        # 2. Acceleration (Price change increasing)
        # Velocity = P_t - P_t-1
        # Acceleration = V_t - V_t-1
        vel_now = latest['close'] - prev['close']
        vel_prev = prev['close'] - df.iloc[-3]['close']
        accel = vel_now - vel_prev
        
        # 3. ATR Expansion (High volatility)
        atr_expansion = latest['atr'] > df['atr'].rolling(20).mean().iloc[-1]
        
        if vol_spike and atr_expansion:
            # PUMP (Accelerating Up)
            if vel_now > 0 and accel > 0:
                return {
                    "action": "LONG",
                    "strength": 3,
                    "leverage": 5,
                    "reason": "🚀 Momentum Pump (Vol+Acc)"
                }
            # DUMP (Accelerating Down)
            elif vel_now < 0 and accel < 0:
                 return {
                    "action": "SHORT",
                    "strength": 3,
                    "leverage": 5,
                    "reason": "📉 Momentum Dump (Vol+Acc)"
                }
        return None

    def should_enter(self, df: pd.DataFrame):
        """
        Analyze market data and return signal
        """
        signal = None
        
        # 1. Check Momentum First (Highest Priority)
        mom_signal = self.check_momentum(df)
        if mom_signal:
            return mom_signal
            
        # Calculate Indicators
        stoch_calc = StochasticTriple(df['high'], df['low'], df['close'])
        stochs = stoch_calc.calculate()
        
        # RSI for filtering
        rsi_ind = RSIIndicator(close=df['close'], window=14)
        rsi = rsi_ind.rsi().iloc[-1]
        
        # EMA Trend Filter (200 EMA)
        ema_200_val = df['ema_200'].iloc[-1] if 'ema_200' in df else df['close'].rolling(200).mean().iloc[-1]
        close = df['close'].iloc[-1]
        is_uptrend = close > ema_200_val
        is_downtrend = close < ema_200_val
        
        # MEAN REVERSION: Allow counter-trend if RSI is extreme
        force_reversal_buy = rsi < 30
        
        # Latest values
        fast_k = stochs['fast']['k'].iloc[-1]
        fast_d = stochs['fast']['d'].iloc[-1]
        mid_k = stochs['mid']['k'].iloc[-1]
        slow_k = stochs['slow']['k'].iloc[-1]
        
        # --- TREND PULLBACK LOGIC (High Quality) ---
        # 1. Bullish Pullback (Buy the dip in Uptrend)
        # Uptrend + Mid/Slow Stoch Oversold + RSI not Overbought
        if is_uptrend and mid_k < 30 and slow_k < 40 and rsi < 60:
             return {
                "action": "LONG",
                "strength": 3,
                "leverage": 5,
                "reason": "📈 Trend Pullback (Buy Dip)"
            }
            
        # 2. Bearish Rally (Sell the bounce in Downtrend)
        # Downtrend + Mid/Slow Stoch Overbought + RSI not Oversold
        if is_downtrend and mid_k > 70 and slow_k > 60 and rsi > 40:
             return {
                "action": "SHORT",
                "strength": 3,
                "leverage": 5,
                "reason": "📉 Trend Rally (Sell Bounce)"
            }
        # -------------------------------------------


        # Previous values (for crossover)
        prev_fast_k = stochs['fast']['k'].iloc[-2]
        prev_fast_d = stochs['fast']['d'].iloc[-2]

        # 1. Triple Convergence (Strongest Signal) - "The King"
        # Logic: All three timeframes are oversold. This is a rare, high-probability reversal.
        if (fast_k < self.oversold and mid_k < self.oversold and slow_k < self.oversold):
            # RSI Confirmation (Just ensure not already overbought, which is unlikely if stoch is low)
            if rsi < 60: 
                 # This signal is powerful enough to ignore minor trend noise.
                 # We give it high strength so AI learns to trust it.
                 strength = 4 
                 signal = {
                    "action": "LONG",
                    "strength": strength,
                    "leverage": 5, # Full confidence
                    "reason": "🔥 Stochastic Triple Convergence (Strong Buy)"
                }

        # 2. Tier 2: Mid-Term Reversal (Queen) - "The Bread & Butter"
        # Logic: Mid (10-6-6) is in value zone (<30) + Fast (5-3-3) turns up (Golden Cross).
        # We don't wait for Slow (20-12-12) to bottom out, as that misses strong trends.
        elif (mid_k < 30 and fast_k < 30):
             # Check Fast Golden Cross (K crosses over D) OR Fast K just turned up sharply
             fast_cross = (fast_k > fast_d and prev_fast_k <= prev_fast_d)
             fast_turning_up = (fast_k > prev_fast_k + 5) # V-shape bounce
             
             if (fast_cross or fast_turning_up) and not signal:
                 if rsi < 60: # Room to grow
                     signal = {
                        "action": "LONG",
                        "strength": 3, # Good strength
                        "leverage": 3,
                        "reason": "Mid-Stoch Support + Fast Turn (Tier 2 Buy)"
                    }

        # 3. Tier 3: Trend Scalp (Knight) - "Buy the Dip"
        # Logic: Strong Uptrend (Price > EMA 200) + Fast Stoch Oversold.
        # In strong trends, waiting for Mid/Slow means missing the boat.
        elif kw_fast_oversold := (fast_k < 20):
             if is_uptrend and not signal: # STRICTLY Trend Following
                 signal = {
                    "action": "LONG",
                    "strength": 2,
                    "leverage": 5, # High leverage allowed because trend is friend
                    "reason": "Uptrend Aggressive Scalp (Tier 3 Buy)"
                }

        # 4. Golden Cross (Fast Only) - Weakest, used as backup
        if (fast_k > fast_d and prev_fast_k < prev_fast_d and fast_k < 40): 
             if not signal or signal['strength'] < 2:
                 if is_uptrend: # Must be with trend

                     signal = {
                        "action": "LONG",
                        "strength": 2,
                        "leverage": 3,
                        "reason": "Stoch Golden Cross at Bottom"
                    }

        # SELL SIGNALS (Short)
        # 1. Triple Convergence Sell (Strongest Signal)
        # Logic: All three timeframes are overbought.
        if (fast_k > self.overbought and mid_k > self.overbought and slow_k > self.overbought):
             # RSI Confirmation (ensure not oversold)
             if rsi > 40:
                 strength = 4
                 signal = {
                    "action": "SHORT",
                    "strength": strength,
                    "leverage": 5,
                    "reason": "🔥 Stochastic Triple Convergence (Strong Sell)"
                }
        
        # 2. Tier 2 Sell: Mid-Term Resistance (Queen)
        # Logic: Mid (10-6-6) is overbought (>70) + Fast (5-3-3) turns down (Dead Cross).
        elif (mid_k > 70 and fast_k > 70):
             fast_cross_down = (fast_k < fast_d and prev_fast_k >= prev_fast_d)
             fast_turning_down = (fast_k < prev_fast_k - 5)
             
             if (fast_cross_down or fast_turning_down) and not signal:
                 if rsi > 40:
                     signal = {
                        "action": "SHORT",
                        "strength": 3,
                        "leverage": 3,
                        "reason": "Mid-Stoch Resistance + Fast Turn (Tier 2 Sell)"
                    }

        # 3. Tier 3 Sell: Trend Scalp (Knight)
        # Logic: Strong Downtrend + Fast Stoch Overbought.
        elif kw_fast_overbought := (fast_k > 80):
             if is_downtrend and not signal:
                 signal = {
                    "action": "SHORT",
                    "strength": 2,
                    "leverage": 5,
                    "reason": "Downtrend Aggressive Scalp (Tier 3 Sell)"
                }

        # 4. Dead Cross (Fast Only) - Backup
        if (fast_k < fast_d and prev_fast_k > prev_fast_d and fast_k > 70):
             if not signal or (signal['action'] == "SHORT" and signal['strength'] < 2):
                  if is_downtrend: # With trend
                      signal = {
                         "action": "SHORT",
                         "strength": 2,
                         "leverage": 3,
                         "reason": "Stoch Dead Cross at Top"
                     }

        return signal
