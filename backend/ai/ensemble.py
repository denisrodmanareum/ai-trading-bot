from typing import List, Dict, Optional
import numpy as np
from loguru import logger
from collections import Counter

from ai.agent import TradingAgent

class EnsembleAgent:
    """
    Ensemble Agent that uses multiple TradingAgent instances to make decisions via voting.
    """
    
    def __init__(self, model_paths: List[str]):
        self.agents: List[TradingAgent] = []
        self.model_paths = model_paths
        self.load_models()
        
    def load_models(self):
        """Load all models in the ensemble"""
        self.agents = []
        try:
            for path in self.model_paths:
                agent = TradingAgent()
                agent.load_model(path)
                self.agents.append(agent)
            
            logger.info(f"Ensemble loaded with {len(self.agents)} models")
            
        except Exception as e:
            logger.error(f"Failed to load ensemble: {e}")
            raise

    def live_predict(self, market_data: Dict) -> int:
        """
        Predict action using voting strategy
        
        Voting Rules:
        - Majority wins.
        - Tie or Split -> Hold (0) for safety.
        """
        if not self.agents:
            raise ValueError("No models loaded in ensemble")
            
        actions = []
        for agent in self.agents:
            try:
                # TradingAgent now returns (action, confidence)
                result = agent.live_predict(market_data)
                if isinstance(result, tuple):
                    action, _ = result
                else:
                    action = result
                actions.append(action)
            except Exception as e:
                logger.error(f"Agent prediction failed: {e}")
                # Skip this agent or default to Hold? 
                # Let's skip to avoid polluting vote with defaults.
                continue
        
        if not actions:
            return 0 # Default Hold
            
        # Voting Logic
        vote_counts = Counter(actions)
        most_common = vote_counts.most_common()
        
        winner_action, winner_count = most_common[0]
        
        # Check for majority or simple plurality?
        # If we have 3 agents:
        # [1, 1, 2] -> 1 wins (2 vs 1)
        # [1, 2, 0] -> 1 wins? (1 vs 1 vs 1) -> No, this is dangerous split.
        # Let's require winner to have > 50% support OR differ significantly?
        
        # Simple Plurality for now, but if tie, take safer option?
        if len(most_common) > 1:
            second_action, second_count = most_common[1]
            if winner_count == second_count:
                # Tie detected
                # If Safe (Hold=0) is involved in tie, prefer Hold?
                if 0 in [winner_action, second_action]:
                    return 0
                
                # If Long(1) vs Short(2), return Hold(0)
                return 0
                
        logger.info(f"Ensemble Vote: {actions} -> {winner_action}")
        return winner_action

    def get_model_info(self) -> Dict:
        """Get ensemble info"""
        return {
            "status": "active_ensemble",
            "type": "ensemble",
            "model_count": len(self.agents),
            "models": self.model_paths
        }
