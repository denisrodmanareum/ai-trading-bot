"""
LSTM Price Predictor
Long Short-Term Memory networks for time series prediction
"""
import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
from loguru import logger
from pathlib import Path


class LSTMPredictor(nn.Module):
    """
    LSTM for price prediction
    
    Architecture:
    - Input: [batch, sequence_length, features]
    - LSTM layers with dropout
    - Fully connected layers
    - Output: [price_change, trend_probability]
    """
    
    def __init__(
        self,
        input_size: int = 20,
        hidden_size: int = 128,
        num_layers: int = 3,
        dropout: float = 0.2
    ):
        super(LSTMPredictor, self).__init__()
        
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        # LSTM layers
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        # Fully connected layers
        self.fc1 = nn.Linear(hidden_size, 64)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
        self.fc2 = nn.Linear(64, 3)  # [price_change, up_prob, down_prob]
        
    def forward(self, x):
        """
        Forward pass
        
        Args:
            x: [batch, seq_len, features]
        
        Returns:
            output: [batch, 3]
        """
        # LSTM
        lstm_out, (h_n, c_n) = self.lstm(x)
        
        # Use last hidden state
        last_hidden = lstm_out[:, -1, :]
        
        # FC layers
        out = self.fc1(last_hidden)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.fc2(out)
        
        return out
    
    def predict(self, x: torch.Tensor) -> Dict:
        """
        Make prediction
        
        Returns:
            {
                'price_change': float,
                'direction': 'UP' | 'DOWN',
                'confidence': float
            }
        """
        self.eval()
        with torch.no_grad():
            output = self.forward(x)
            
            price_change = output[0, 0].item()
            up_prob = torch.sigmoid(output[0, 1]).item()
            down_prob = torch.sigmoid(output[0, 2]).item()
            
            # Direction
            if up_prob > down_prob:
                direction = 'UP'
                confidence = up_prob
            else:
                direction = 'DOWN'
                confidence = down_prob
            
            return {
                'price_change': price_change,
                'direction': direction,
                'confidence': round(confidence, 3)
            }


class TransformerPredictor(nn.Module):
    """
    Transformer for price prediction
    Uses attention mechanism to focus on important time steps
    """
    
    def __init__(
        self,
        d_model: int = 128,
        nhead: int = 8,
        num_layers: int = 4,
        dim_feedforward: int = 512,
        dropout: float = 0.1
    ):
        super(TransformerPredictor, self).__init__()
        
        self.d_model = d_model
        
        # Input embedding
        self.input_linear = nn.Linear(20, d_model)  # 20 features → d_model
        
        # Positional encoding
        self.pos_encoder = PositionalEncoding(d_model, dropout)
        
        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers
        )
        
        # Output layers
        self.fc1 = nn.Linear(d_model, 64)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
        self.fc2 = nn.Linear(64, 3)
        
    def forward(self, x):
        """
        Forward pass
        
        Args:
            x: [batch, seq_len, features]
        """
        # Embed input
        x = self.input_linear(x)
        x = self.pos_encoder(x)
        
        # Transformer
        transformer_out = self.transformer_encoder(x)
        
        # Use last time step
        last_output = transformer_out[:, -1, :]
        
        # FC layers
        out = self.fc1(last_output)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.fc2(out)
        
        return out
    
    def predict(self, x: torch.Tensor) -> Dict:
        """Make prediction"""
        self.eval()
        with torch.no_grad():
            output = self.forward(x)
            
            price_change = output[0, 0].item()
            up_prob = torch.sigmoid(output[0, 1]).item()
            down_prob = torch.sigmoid(output[0, 2]).item()
            
            direction = 'UP' if up_prob > down_prob else 'DOWN'
            confidence = up_prob if direction == 'UP' else down_prob
            
            return {
                'price_change': price_change,
                'direction': direction,
                'confidence': round(confidence, 3)
            }


class PositionalEncoding(nn.Module):
    """
    Positional encoding for Transformer
    """
    
    def __init__(self, d_model: int, dropout: float = 0.1, max_len: int = 5000):
        super(PositionalEncoding, self).__init__()
        self.dropout = nn.Dropout(p=dropout)
        
        # Create positional encoding
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model)
        )
        
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        
        self.register_buffer('pe', pe)
    
    def forward(self, x):
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)


class DeepLearningPredictor:
    """
    Deep Learning predictor manager
    Handles LSTM and Transformer models
    """
    
    def __init__(self, model_type: str = 'lstm', model_path: Optional[str] = None):
        """
        Args:
            model_type: 'lstm' or 'transformer'
            model_path: Path to saved model
        """
        self.model_type = model_type
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Create model
        if model_type == 'lstm':
            self.model = LSTMPredictor()
        elif model_type == 'transformer':
            self.model = TransformerPredictor()
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        self.model.to(self.device)
        
        # Load if path provided
        if model_path and Path(model_path).exists():
            self.load_model(model_path)
            logger.info(f"Loaded {model_type} model from {model_path}")
        else:
            logger.info(f"Created new {model_type} model")
    
    def prepare_data(
        self,
        df: pd.DataFrame,
        sequence_length: int = 100
    ) -> Tuple[torch.Tensor, np.ndarray]:
        """
        Prepare data for prediction
        
        Args:
            df: DataFrame with OHLCV + indicators
            sequence_length: Number of time steps to use
        
        Returns:
            (X: torch.Tensor, prices: np.ndarray)
        """
        # Select features
        feature_cols = [
            'close', 'volume', 'rsi', 'macd', 'signal',
            'bb_upper', 'bb_middle', 'bb_lower', 'atr',
            'stoch_k', 'stoch_d', 'adx', 'ema_20', 'ema_50',
            'volume_ma', 'obv', 'momentum', 'roc', 'mfi', 'hist_vol'
        ]
        
        # Use available features
        available_features = [col for col in feature_cols if col in df.columns]
        
        if len(available_features) < 5:
            raise ValueError("Not enough features in DataFrame")
        
        # Normalize
        data = df[available_features].values
        data = (data - np.mean(data, axis=0)) / (np.std(data, axis=0) + 1e-8)
        
        # Create sequences
        X = []
        if len(data) >= sequence_length:
            X.append(data[-sequence_length:])
        else:
            # Pad if not enough data
            pad_length = sequence_length - len(data)
            padded = np.vstack([np.zeros((pad_length, data.shape[1])), data])
            X.append(padded)
        
        X = np.array(X)
        X_tensor = torch.FloatTensor(X).to(self.device)
        
        return X_tensor, df['close'].values
    
    def predict_next_movement(self, df: pd.DataFrame) -> Dict:
        """
        Predict next price movement
        
        Returns:
            {
                'direction': 'UP' | 'DOWN',
                'magnitude': float,
                'confidence': float,
                'model': str
            }
        """
        try:
            X, prices = self.prepare_data(df)
            prediction = self.model.predict(X)
            
            # Add magnitude estimate
            current_price = prices[-1]
            predicted_change_pct = prediction['price_change']
            magnitude = abs(predicted_change_pct)
            
            return {
                'direction': prediction['direction'],
                'magnitude': round(magnitude, 3),
                'confidence': prediction['confidence'],
                'model': self.model_type,
                'current_price': current_price
            }
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return {
                'direction': 'HOLD',
                'magnitude': 0.0,
                'confidence': 0.5,
                'model': self.model_type,
                'error': str(e)
            }
    
    def save_model(self, path: str):
        """Save model to file"""
        torch.save(self.model.state_dict(), path)
        logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str):
        """Load model from file"""
        self.model.load_state_dict(torch.load(path, map_location=self.device))
        self.model.eval()
        logger.info(f"Model loaded from {path}")
