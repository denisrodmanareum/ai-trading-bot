"""
Advanced Feature Engineering
Additional technical indicators and market data
"""
import pandas as pd
import numpy as np
from typing import Dict, List
from loguru import logger


class AdvancedFeatureEngine:
    """
    Calculates advanced features for AI trading:
    - Volume analysis
    - Order flow
    - Momentum indicators
    - Market microstructure
    """
    
    def __init__(self):
        self.feature_history = []
    
    def calculate_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Volume-based features
        """
        # Volume MA ratio
        df['volume_ma_20'] = df['volume'].rolling(window=20).mean()
        df['volume_ma_ratio'] = df['volume'] / df['volume_ma_20']
        
        # Volume trend
        df['volume_trend'] = df['volume'].pct_change(5)
        
        # Price-Volume correlation
        df['pv_corr'] = df['close'].rolling(window=20).corr(df['volume'])
        
        # On-Balance Volume (OBV)
        df['obv'] = (np.sign(df['close'].diff()) * df['volume']).cumsum()
        df['obv_ma'] = df['obv'].rolling(window=20).mean()
        df['obv_divergence'] = df['obv'] - df['obv_ma']
        
        return df
    
    def calculate_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Momentum indicators
        """
        # Price momentum (multiple timeframes)
        df['momentum_3'] = df['close'].pct_change(3)
        df['momentum_5'] = df['close'].pct_change(5)
        df['momentum_10'] = df['close'].pct_change(10)
        df['momentum_20'] = df['close'].pct_change(20)
        
        # Rate of Change (ROC)
        df['roc_14'] = ((df['close'] - df['close'].shift(14)) / df['close'].shift(14)) * 100
        
        # Money Flow Index (MFI)
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        money_flow = typical_price * df['volume']
        
        positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0).rolling(14).sum()
        negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0).rolling(14).sum()
        
        mfi = 100 - (100 / (1 + positive_flow / (negative_flow + 1e-10)))
        df['mfi'] = mfi
        
        # Acceleration (2nd derivative of price)
        df['price_velocity'] = df['close'].diff()
        df['price_acceleration'] = df['price_velocity'].diff()
        
        return df
    
    def calculate_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Volatility and range indicators
        """
        # Historical Volatility
        df['hist_vol_10'] = df['close'].pct_change().rolling(10).std() * np.sqrt(10)
        df['hist_vol_20'] = df['close'].pct_change().rolling(20).std() * np.sqrt(20)
        
        # High-Low Range
        df['hl_range'] = (df['high'] - df['low']) / df['close']
        df['hl_range_ma'] = df['hl_range'].rolling(20).mean()
        df['hl_range_ratio'] = df['hl_range'] / df['hl_range_ma']
        
        # Keltner Channel (ATR-based)
        ema_20 = df['close'].ewm(span=20).mean()
        df['keltner_upper'] = ema_20 + (df['atr'] * 2)
        df['keltner_lower'] = ema_20 - (df['atr'] * 2)
        df['keltner_position'] = (df['close'] - df['keltner_lower']) / (df['keltner_upper'] - df['keltner_lower'])
        
        return df
    
    def calculate_trend_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Trend strength and direction
        """
        # ADX (if not already calculated)
        if 'adx' not in df.columns:
            df['adx'] = self._calculate_adx(df)
        
        # Supertrend
        df = self._calculate_supertrend(df, period=10, multiplier=3)
        
        # Linear regression slope
        df['lr_slope_20'] = df['close'].rolling(20).apply(self._linear_regression_slope, raw=True)
        
        # Parabolic SAR
        df = self._calculate_psar(df)
        
        return df
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate ADX"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = dx.rolling(window=period).mean()
        
        return adx
    
    def _calculate_supertrend(self, df: pd.DataFrame, period: int = 10, multiplier: int = 3) -> pd.DataFrame:
        """Calculate Supertrend indicator"""
        hl_avg = (df['high'] + df['low']) / 2
        atr = df['atr'] if 'atr' in df.columns else (df['high'] - df['low']).rolling(period).mean()
        
        upper_band = hl_avg + (multiplier * atr)
        lower_band = hl_avg - (multiplier * atr)
        
        df['supertrend_upper'] = upper_band
        df['supertrend_lower'] = lower_band
        
        # Supertrend direction (1 = uptrend, -1 = downtrend)
        df['supertrend'] = np.where(df['close'] > lower_band, 1, -1)
        
        return df
    
    def _linear_regression_slope(self, y):
        """Calculate linear regression slope"""
        if len(y) < 2:
            return 0
        x = np.arange(len(y))
        slope = np.polyfit(x, y, 1)[0]
        return slope
    
    def _calculate_psar(self, df: pd.DataFrame, af_start=0.02, af_max=0.2) -> pd.DataFrame:
        """Calculate Parabolic SAR"""
        # Simplified PSAR implementation
        psar = df['close'].copy()
        bull = True
        af = af_start
        ep = df['low'].iloc[0]
        hp = df['high'].iloc[0]
        lp = df['low'].iloc[0]
        
        for i in range(1, len(df)):
            if bull:
                psar.iloc[i] = psar.iloc[i-1] + af * (hp - psar.iloc[i-1])
                if df['low'].iloc[i] < psar.iloc[i]:
                    bull = False
                    psar.iloc[i] = hp
                    ep = df['low'].iloc[i]
                    af = af_start
            else:
                psar.iloc[i] = psar.iloc[i-1] - af * (psar.iloc[i-1] - lp)
                if df['high'].iloc[i] > psar.iloc[i]:
                    bull = True
                    psar.iloc[i] = lp
                    ep = df['high'].iloc[i]
                    af = af_start
            
            if bull:
                if df['high'].iloc[i] > hp:
                    hp = df['high'].iloc[i]
                    af = min(af + af_start, af_max)
            else:
                if df['low'].iloc[i] < lp:
                    lp = df['low'].iloc[i]
                    af = min(af + af_start, af_max)
        
        df['psar'] = psar
        return df
    
    def calculate_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all advanced features
        """
        logger.info("Calculating advanced features...")
        
        try:
            df = self.calculate_volume_features(df)
            df = self.calculate_momentum_features(df)
            df = self.calculate_volatility_features(df)
            df = self.calculate_trend_features(df)
            
            # Fill NaN values
            df = df.fillna(method='bfill').fillna(method='ffill').fillna(0)
            
            logger.info(f"Added {len(df.columns)} features")
            return df
            
        except Exception as e:
            logger.error(f"Feature calculation failed: {e}")
            return df
    
    def get_feature_importance(self, feature_names: List[str], model) -> Dict:
        """
        Calculate feature importance (if model supports it)
        """
        try:
            # For tree-based models
            if hasattr(model, 'feature_importances_'):
                importances = model.feature_importances_
                feature_importance = dict(zip(feature_names, importances))
                
                # Sort by importance
                sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
                
                return {
                    'features': [f[0] for f in sorted_features[:20]],  # Top 20
                    'importances': [f[1] for f in sorted_features[:20]]
                }
        except Exception as e:
            logger.warning(f"Could not calculate feature importance: {e}")
        
        return {'features': [], 'importances': []}
