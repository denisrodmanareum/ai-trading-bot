"""
LSTM Training Script
"""
import asyncio
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import pandas as pd
import numpy as np
from datetime import datetime
from loguru import logger
import os
import sys

# Add parent directory to path to import ai modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ai.deep_models.lstm_predictor import LSTMPredictor, DeepLearningPredictor
from ai.trainer import fetch_training_data
from app.core.config import settings

async def train_lstm(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    days: int = 30,
    epochs: int = 50,
    batch_size: int = 32,
    sequence_length: int = 100,
    learning_rate: float = 0.001
):
    """LSTM 모델 학습 및 저장"""
    logger.info(f"🚀 Starting LSTM training for {symbol} ({interval})...")
    
    # 1. 데이터 가져오기
    df = await fetch_training_data(symbol, interval, days)
    
    if len(df) < sequence_length + 10:
        logger.error(f"Not enough data for training: {len(df)} candles")
        return
    
    # 2. 데이터 준비
    predictor = DeepLearningPredictor(model_type='lstm')
    
    # 피처 컬럼 정의 (features.py 참고)
    feature_cols = [
        'close', 'volume', 'rsi', 'macd', 'signal',
        'bb_upper', 'bb_middle', 'bb_lower', 'atr',
        'stoch_k', 'stoch_d', 'ema_9', 'ema_21', 'ema_50',
        'returns', 'log_returns', 'volume_ratio', 'high_low_ratio',
        'candle_body', 'upper_shadow'
    ]
    
    # 가용 피처만 선택
    available_features = [col for col in feature_cols if col in df.columns]
    data = df[available_features].values
    
    # 정규화
    mean = np.mean(data, axis=0)
    std = np.std(data, axis=0) + 1e-8
    data_norm = (data - mean) / std
    
    # 타겟 생성 (다음 캔들의 수익률)
    # predictor.py의 fc2 출력이 3개 [price_change, up_prob, down_prob] 임을 고려
    # 여기서는 간단하게 다음 캔들의 변화량과 방향을 학습
    X, y = [], []
    for i in range(len(data_norm) - sequence_length):
        X.append(data_norm[i:i+sequence_length])
        
        # 다음 캔들의 로그 수익률
        next_return = df['log_returns'].iloc[i+sequence_length]
        
        # [change, up, down] 형식의 타겟
        # up/down은 임계값 0.001 (0.1%) 기준으로 설정
        up = 1.0 if next_return > 0.001 else 0.0
        down = 1.0 if next_return < -0.001 else 0.0
        y.append([next_return * 100, up, down]) # 수익률은 % 단위로 스케일링
    
    X = torch.FloatTensor(np.array(X)).to(predictor.device)
    y = torch.FloatTensor(np.array(y)).to(predictor.device)
    
    dataset = TensorDataset(X, y)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    # 3. 모델 설정
    model = predictor.model
    criterion = nn.MSELoss() # 간단하게 MSE 사용 (실제로는 복합 손실 함수 고려 가능)
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    
    # 4. 학습 루프
    model.train()
    for epoch in range(epochs):
        epoch_loss = 0
        for batch_X, batch_y in loader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
        
        if (epoch + 1) % 10 == 0:
            logger.info(f"Epoch [{epoch+1}/{epochs}], Loss: {epoch_loss/len(loader):.6f}")
    
    # 5. 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    model_name = f"lstm_{symbol}_{interval}_{timestamp}.pt"
    save_path = os.path.join(settings.AI_MODEL_PATH, model_name)
    
    os.makedirs(settings.AI_MODEL_PATH, exist_ok=True)
    predictor.save_model(save_path)
    
    # 기존 같은 interval 모델 삭제 (최신 하나만 유지)
    import glob
    pattern = os.path.join(settings.AI_MODEL_PATH, f"lstm_{symbol}_{interval}_*.pt")
    existing = sorted(glob.glob(pattern), reverse=True)
    for old in existing[1:]:
        try:
            os.remove(old)
            logger.info(f"🗑️ Cleaned up old LSTM model: {os.path.basename(old)}")
        except:
            pass
            
    logger.info(f"✅ LSTM training finished. Model saved: {model_name}")
    return save_path

if __name__ == "__main__":
    # 순차적 학습 실행
    async def run_all():
        # 1시간봉 학습
        await train_lstm(interval="1h", days=30, epochs=30)
        # 1분봉 학습
        await train_lstm(interval="1m", days=3, epochs=30) # 1분봉은 데이터가 많으므로 날짜 축소
        
    asyncio.run(run_all())
