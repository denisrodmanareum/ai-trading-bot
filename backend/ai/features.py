"""
Technical Indicators Feature Engineering
"""
import pandas as pd
import numpy as np
from ta.trend import MACD, EMAIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import VolumeWeightedAveragePrice
from loguru import logger


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add technical indicators to dataframe
    
    Indicators:
    - RSI (Relative Strength Index)
    - MACD (Moving Average Convergence Divergence)
    - Bollinger Bands
    - ATR (Average True Range)
    - EMA (Exponential Moving Average)
    - Stochastic Oscillator
    - VWAP (Volume Weighted Average Price)
    """
    try:
        logger.info("Calculating technical indicators...")
        
        # Make a copy to avoid modifying original
        df = df.copy()
        
        # RSI
        rsi = RSIIndicator(close=df['close'], window=14)
        df['rsi'] = rsi.rsi()
        
        # MACD
        macd = MACD(close=df['close'], window_slow=26, window_fast=12, window_sign=9)
        df['macd'] = macd.macd()
        df['signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()
        
        # Bollinger Bands
        bb = BollingerBands(close=df['close'], window=20, window_dev=2)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_middle'] = bb.bollinger_mavg()
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_width'] = bb.bollinger_wband()
        df['bb_pct'] = bb.bollinger_pband()
        
        # ATR (Average True Range)
        atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14)
        df['atr'] = atr.average_true_range()
        
        # EMA
        ema_9 = EMAIndicator(close=df['close'], window=9)
        ema_21 = EMAIndicator(close=df['close'], window=21)
        ema_50 = EMAIndicator(close=df['close'], window=50)
        
        df['ema_9'] = ema_9.ema_indicator()
        df['ema_21'] = ema_21.ema_indicator()
        df['ema_50'] = ema_50.ema_indicator()
        
        # Stochastic Oscillator
        stoch = StochasticOscillator(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            window=14,
            smooth_window=3
        )
        df['stoch_k'] = stoch.stoch()
        df['stoch_d'] = stoch.stoch_signal()
        
        # Price momentum
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # Volume indicators
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Price position relative to high/low
        df['high_low_ratio'] = (df['close'] - df['low']) / (df['high'] - df['low'])
        
        # --- NEW: Candle Shape Features (Wonyoddie/Pattern Recognition) ---
        # Body Ratio: Size of body relative to total range (0.0 to 1.0)
        df['candle_range'] = df['high'] - df['low']
        # Avoid division by zero
        df['candle_range'] = df['candle_range'].replace(0, 0.000001)
        
        df['candle_body'] = abs(df['close'] - df['open']) / df['candle_range']
        df['upper_shadow'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['candle_range']
        df['lower_shadow'] = (df[['open', 'close']].min(axis=1) - df['low']) / df['candle_range']
        
        # -----------------------------------------------------------------
        
        # Fill NaN values
        df = df.bfill().ffill()
        
        logger.info(f"Added {len(df.columns) - 12} technical indicators")
        return df
        
    except Exception as e:
        logger.error(f"Failed to calculate indicators: {e}")
        raise


def calculate_live_indicators(klines: list) -> dict:
    """
    Calculate indicators from recent klines for live trading
    
    Args:
        klines: List of recent klines (at least 50 for proper indicator calculation)
        
    Returns:
        Dictionary of current indicator values
    """
    try:
        # Convert to dataframe
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        # Add indicators
        df = add_technical_indicators(df)
        
        # Get latest values
        latest = df.iloc[-1]
        
        return {
            'close': float(latest['close']),
            'volume': float(latest['volume']),
            'rsi': float(latest['rsi']),
            'macd': float(latest['macd']),
            'signal': float(latest['signal']),
            'bb_upper': float(latest['bb_upper']),
            'bb_lower': float(latest['bb_lower']),
            'bb_middle': float(latest['bb_middle']),
            'atr': float(latest['atr']),
            'ema_9': float(latest['ema_9']),
            'ema_21': float(latest['ema_21']),
            'ema_50': float(latest['ema_50']),
            'stoch_k': float(latest['stoch_k']),
            'stoch_d': float(latest['stoch_d'])
        }
        
    except Exception as e:
        logger.error(f"Failed to calculate live indicators: {e}")
        raise
