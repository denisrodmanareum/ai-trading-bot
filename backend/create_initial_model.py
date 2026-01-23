"""
간단한 초기 모델 생성 스크립트
빠른 테스트용 - 실제 거래에는 충분한 학습이 필요합니다
"""
import asyncio
from datetime import datetime
from ai.trainer import train_agent
from loguru import logger

async def create_quick_model():
    """빠른 테스트용 모델 생성"""
    logger.info("🚀 간단한 초기 모델 생성 시작...")
    logger.info("⚠️  이 모델은 테스트용입니다. 실거래에는 충분한 학습이 필요합니다.")
    
    try:
        model_path = await train_agent(
            symbol="BTCUSDT",
            interval="1h",
            days=7,              # 7일치 데이터
            episodes=500,        # 빠른 학습을 위해 500 에피소드
            leverage=5,
            reward_strategy="simple"
        )
        
        logger.success(f"✅ 모델 생성 완료: {model_path}")
        logger.info("💡 이제 프론트엔드에서 이 모델을 로드할 수 있습니다.")
        
    except Exception as e:
        logger.error(f"❌ 모델 생성 실패: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(create_quick_model())
