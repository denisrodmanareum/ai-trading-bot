"""
Hybrid AI System
Combines PPO + LSTM + Ensemble for better predictions
"""
from typing import Dict, Tuple
import numpy as np
from loguru import logger
from ai.agent import TradingAgent
from ai.ensemble import EnsembleAgent


class HybridAI:
    """
    하이브리드 AI 시스템
    - PPO Agent (강화학습)
    - LSTM Predictor (가격 예측) - Optional
    - Ensemble (복수 모델) - Optional
    """
    
    def __init__(self):
        self.ppo_agent = None
        self.lstm_predictor = None
        self.ensemble = None
        self.mode = "ppo_only"  # "ppo_only", "ppo_ensemble", "full_hybrid"
    
    def load_ppo(self, model_path: str):
        """PPO 모델 로드"""
        try:
            self.ppo_agent = TradingAgent()
            self.ppo_agent.load_model(model_path)
            logger.info(f"✅ PPO model loaded: {model_path}")
            self.mode = "ppo_only"
        except Exception as e:
            logger.error(f"Failed to load PPO model: {e}")
            raise
    
    def load_ensemble(self, model_paths: list):
        """앙상블 모델 로드"""
        try:
            self.ensemble = EnsembleAgent(model_paths)
            logger.info(f"✅ Ensemble loaded with {len(model_paths)} models")
            self.mode = "ppo_ensemble"
        except Exception as e:
            logger.error(f"Failed to load ensemble: {e}")
            self.ensemble = None
    
    def load_lstm(self, model_path: str):
        """LSTM 모델 로드 (Optional)"""
        try:
            from ai.deep_models.lstm_predictor import LSTMPredictor
            import torch
            
            self.lstm_predictor = LSTMPredictor()
            self.lstm_predictor.load_state_dict(torch.load(model_path))
            self.lstm_predictor.eval()
            logger.info(f"✅ LSTM model loaded: {model_path}")
            self.mode = "full_hybrid"
        except Exception as e:
            logger.warning(f"LSTM model not available: {e}")
            self.lstm_predictor = None
    
    async def predict(self, market_data: Dict) -> Tuple[int, float]:
        """
        통합 예측
        
        Returns:
            (action, confidence)
            action: 0=HOLD, 1=LONG, 2=SHORT, 3=CLOSE
            confidence: 0.0~1.0
        """
        if self.mode == "ppo_only":
            return await self._predict_ppo_only(market_data)
        elif self.mode == "ppo_ensemble":
            return await self._predict_with_ensemble(market_data)
        elif self.mode == "full_hybrid":
            return await self._predict_full_hybrid(market_data)
        else:
            return 0, 0.0
    
    async def _predict_ppo_only(self, market_data: Dict) -> Tuple[int, float]:
        """PPO만 사용"""
        if not self.ppo_agent:
            return 0, 0.0
        
        try:
            action, confidence = self.ppo_agent.live_predict(market_data)
            return action, confidence
        except Exception as e:
            logger.error(f"PPO prediction failed: {e}")
            return 0, 0.0
    
    async def _predict_with_ensemble(self, market_data: Dict) -> Tuple[int, float]:
        """
        PPO + Ensemble 투표
        """
        if not self.ppo_agent:
            return 0, 0.0
        
        try:
            # 1. PPO 예측
            ppo_action, ppo_conf = self.ppo_agent.live_predict(market_data)
            
            # 2. Ensemble 예측 (있으면)
            if self.ensemble:
                # Ensemble의 live_predict는 confidence 없음
                ensemble_action = self.ensemble.live_predict(market_data)
                
                # 투표: 일치하면 높은 신뢰도, 불일치하면 낮은 신뢰도
                if ppo_action == ensemble_action:
                    final_action = ppo_action
                    final_conf = min(1.0, ppo_conf * 1.2)  # 일치 시 부스트
                else:
                    # 불일치 - PPO의 신뢰도가 높으면 PPO 따름
                    if ppo_conf > 0.6:
                        final_action = ppo_action
                        final_conf = ppo_conf * 0.8  # 페널티
                    else:
                        # 신뢰도 낮으면 HOLD
                        final_action = 0
                        final_conf = 0.3
                
                logger.debug(
                    f"Ensemble vote: PPO={ppo_action}({ppo_conf:.2f}), "
                    f"Ensemble={ensemble_action} → Final={final_action}({final_conf:.2f})"
                )
                
                return final_action, final_conf
            else:
                return ppo_action, ppo_conf
                
        except Exception as e:
            logger.error(f"Ensemble prediction failed: {e}")
            return 0, 0.0
    
    async def _predict_full_hybrid(self, market_data: Dict) -> Tuple[int, float]:
        """
        PPO + LSTM + Ensemble 통합
        """
        if not self.ppo_agent:
            return 0, 0.0
        
        try:
            # 1. PPO 예측
            ppo_action, ppo_conf = self.ppo_agent.live_predict(market_data)
            
            # 2. LSTM 가격 예측 (있으면)
            lstm_action = 0
            if self.lstm_predictor:
                lstm_pred = await self._predict_price_with_lstm(market_data)
                # 가격 예측을 액션으로 변환
                if lstm_pred > 0.5:  # 상승 예측
                    lstm_action = 1  # LONG
                elif lstm_pred < -0.5:  # 하락 예측
                    lstm_action = 2  # SHORT
                else:
                    lstm_action = 0  # HOLD
            
            # 3. Ensemble 예측 (있으면)
            ensemble_action = 0
            if self.ensemble:
                ensemble_action = self.ensemble.live_predict(market_data)
            
            # 4. 통합 투표
            votes = [ppo_action]
            if lstm_action != 0:
                votes.append(lstm_action)
            if ensemble_action != 0 and self.ensemble:
                votes.append(ensemble_action)
            
            # 다수결
            from collections import Counter
            vote_counts = Counter(votes)
            final_action = vote_counts.most_common(1)[0][0]
            
            # 신뢰도: 일치도 기반
            agreement = vote_counts[final_action] / len(votes)
            final_conf = ppo_conf * agreement
            
            logger.debug(
                f"Full hybrid: PPO={ppo_action}, LSTM={lstm_action}, "
                f"Ensemble={ensemble_action} → Final={final_action}({final_conf:.2f})"
            )
            
            return final_action, final_conf
            
        except Exception as e:
            logger.error(f"Full hybrid prediction failed: {e}")
            return 0, 0.0
    
    async def _predict_price_with_lstm(self, market_data: Dict) -> float:
        """
        LSTM으로 가격 변화 예측
        
        Returns:
            Predicted price change (%)
        """
        try:
            import torch
            
            # 시퀀스 데이터 준비 (간단 버전 - 실제로는 historical data 필요)
            # 여기서는 placeholder
            sequence = torch.zeros(1, 50, 20)  # [batch, seq_len, features]
            
            with torch.no_grad():
                prediction = self.lstm_predictor(sequence)
            
            # 예측 값 추출
            price_change = float(prediction[0, 0])
            
            return price_change
            
        except Exception as e:
            logger.error(f"LSTM prediction failed: {e}")
            return 0.0
    
    def get_status(self) -> Dict:
        """시스템 상태"""
        return {
            'mode': self.mode,
            'ppo_loaded': self.ppo_agent is not None,
            'lstm_loaded': self.lstm_predictor is not None,
            'ensemble_loaded': self.ensemble is not None,
            'ensemble_models': len(self.ensemble.agents) if self.ensemble else 0
        }
