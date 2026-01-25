"""
Slippage Manager
Manages order execution with slippage control and smart order routing
"""
from typing import Dict, Optional, Tuple
from loguru import logger
import asyncio


class SlippageManager:
    """
    슬리피지 관리 및 스마트 주문 시스템
    - 오더북 분석으로 슬리피지 예측
    - 최적 주문 방식 선택 (Market vs Limit)
    - 체결가 추적 및 분석
    """
    
    def __init__(self, exchange_client):
        self.exchange_client = exchange_client
        self.slippage_history = {}  # symbol -> list of slippage records
        self.max_slippage_pct = 0.1  # Default: 0.1% max slippage
        
    async def estimate_slippage(
        self, 
        symbol: str, 
        quantity: float, 
        side: str
    ) -> Dict:
        """
        오더북 기반 슬리피지 예측
        
        Args:
            symbol: 거래 심볼
            quantity: 주문 수량
            side: "BUY" or "SELL"
            
        Returns:
            {
                'estimated_slippage_pct': float,
                'avg_fill_price': float,
                'best_price': float,
                'liquidity_ok': bool
            }
        """
        try:
            # 오더북 조회 (20단계)
            orderbook = await self.exchange_client.get_orderbook(symbol, limit=20)
            
            if side == "BUY":
                # Ask 사이드 분석
                orders = orderbook['asks']
                best_price = float(orders[0][0])
            else:
                # Bid 사이드 분석
                orders = orderbook['bids']
                best_price = float(orders[0][0])
            
            # 필요한 유동성 계산
            total_cost = 0.0
            total_qty = 0.0
            
            for price_str, qty_str in orders:
                price = float(price_str)
                available_qty = float(qty_str)
                
                if total_qty >= quantity:
                    break
                
                needed_qty = min(quantity - total_qty, available_qty)
                total_cost += price * needed_qty
                total_qty += needed_qty
            
            # 평균 체결가 계산
            if total_qty > 0:
                avg_fill_price = total_cost / total_qty
                
                # 슬리피지 계산
                if side == "BUY":
                    slippage_pct = (avg_fill_price - best_price) / best_price * 100
                else:
                    slippage_pct = (best_price - avg_fill_price) / best_price * 100
                
                # 유동성 충분한지 체크
                liquidity_ok = total_qty >= quantity * 0.95  # 95% 이상 체결 가능
                
                return {
                    'estimated_slippage_pct': slippage_pct,
                    'avg_fill_price': avg_fill_price,
                    'best_price': best_price,
                    'liquidity_ok': liquidity_ok,
                    'available_liquidity': total_qty
                }
            else:
                return {
                    'estimated_slippage_pct': 0.0,
                    'avg_fill_price': best_price,
                    'best_price': best_price,
                    'liquidity_ok': False,
                    'available_liquidity': 0.0
                }
                
        except Exception as e:
            logger.error(f"Slippage estimation failed for {symbol}: {e}")
            return {
                'estimated_slippage_pct': 0.0,
                'avg_fill_price': 0.0,
                'best_price': 0.0,
                'liquidity_ok': True,
                'available_liquidity': 0.0
            }
    
    async def smart_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        max_slippage: Optional[float] = None
    ) -> Dict:
        """
        스마트 주문 실행
        - 슬리피지 예측
        - 최적 주문 방식 선택
        - 실행 및 결과 추적
        
        Args:
            symbol: 거래 심볼
            side: "BUY" or "SELL"
            quantity: 주문 수량
            max_slippage: 최대 허용 슬리피지 (%, None이면 기본값)
            
        Returns:
            Order result with actual slippage
        """
        max_slip = max_slippage or self.max_slippage_pct
        
        # 1. 슬리피지 예측
        estimation = await self.estimate_slippage(symbol, quantity, side)
        
        logger.info(
            f"📊 Slippage Estimate {symbol}: "
            f"{estimation['estimated_slippage_pct']:.3f}% "
            f"(Best: {estimation['best_price']:.2f} → Avg: {estimation['avg_fill_price']:.2f})"
        )
        
        # 2. 유동성 체크
        if not estimation['liquidity_ok']:
            logger.warning(
                f"⚠️ Low liquidity for {symbol}: "
                f"{estimation['available_liquidity']:.4f} < {quantity:.4f}"
            )
            # 수량 조정 고려
            if estimation['available_liquidity'] > 0:
                quantity = estimation['available_liquidity'] * 0.9  # 90%만 사용
                logger.info(f"📉 Adjusted quantity to {quantity:.4f}")
        
        # 3. 주문 방식 결정
        if estimation['estimated_slippage_pct'] <= max_slip:
            # 슬리피지 OK → 시장가 주문
            logger.info(f"✅ Using MARKET order (slippage within limit)")
            order = await self.exchange_client.place_market_order(symbol, side, quantity)
            order_type = "MARKET"
            
        else:
            # 슬리피지 높음 → LIMIT 주문 (IOC - Immediate or Cancel)
            logger.warning(
                f"⚠️ High slippage ({estimation['estimated_slippage_pct']:.3f}%), "
                f"using LIMIT order"
            )
            
            # LIMIT 가격 설정 (빠른 체결을 위해 약간 불리하게)
            ticker = await self.exchange_client.get_ticker(symbol)
            
            if side == "BUY":
                # Ask + 0.05% 프리미엄
                limit_price = float(ticker['askPrice']) * 1.0005
            else:
                # Bid - 0.05% 디스카운트
                limit_price = float(ticker['bidPrice']) * 0.9995
            
            order = await self.exchange_client.place_limit_order(
                symbol, side, quantity, limit_price, time_in_force='IOC'
            )
            order_type = "LIMIT_IOC"
        
        # 4. 실제 슬리피지 계산
        if order and 'avgPrice' in order:
            actual_fill_price = float(order.get('avgPrice', 0))
            
            if actual_fill_price > 0:
                if side == "BUY":
                    actual_slippage = (actual_fill_price - estimation['best_price']) / estimation['best_price'] * 100
                else:
                    actual_slippage = (estimation['best_price'] - actual_fill_price) / estimation['best_price'] * 100
                
                # 히스토리 기록
                self._record_slippage(symbol, {
                    'estimated': estimation['estimated_slippage_pct'],
                    'actual': actual_slippage,
                    'order_type': order_type,
                    'quantity': quantity
                })
                
                logger.info(
                    f"📈 Actual Slippage {symbol}: {actual_slippage:.3f}% "
                    f"(Estimated: {estimation['estimated_slippage_pct']:.3f}%)"
                )
                
                order['slippage_pct'] = actual_slippage
        
        return order
    
    def _record_slippage(self, symbol: str, record: Dict):
        """슬리피지 기록 저장"""
        if symbol not in self.slippage_history:
            self.slippage_history[symbol] = []
        
        self.slippage_history[symbol].append(record)
        
        # 최근 100개만 유지
        if len(self.slippage_history[symbol]) > 100:
            self.slippage_history[symbol] = self.slippage_history[symbol][-100:]
    
    def get_average_slippage(self, symbol: str) -> float:
        """심볼별 평균 슬리피지"""
        if symbol not in self.slippage_history or len(self.slippage_history[symbol]) == 0:
            return 0.0
        
        recent = self.slippage_history[symbol][-20:]  # 최근 20개
        avg_slip = sum(r['actual'] for r in recent) / len(recent)
        
        return avg_slip
    
    def get_slippage_stats(self) -> Dict:
        """전체 슬리피지 통계"""
        if not self.slippage_history:
            return {
                'avg_slippage': 0.0,
                'max_slippage': 0.0,
                'total_cost_pct': 0.0
            }
        
        all_records = []
        for records in self.slippage_history.values():
            all_records.extend(records)
        
        if not all_records:
            return {
                'avg_slippage': 0.0,
                'max_slippage': 0.0,
                'total_cost_pct': 0.0
            }
        
        actual_slippages = [r['actual'] for r in all_records]
        
        return {
            'avg_slippage': sum(actual_slippages) / len(actual_slippages),
            'max_slippage': max(actual_slippages),
            'min_slippage': min(actual_slippages),
            'total_records': len(all_records),
            'market_orders': sum(1 for r in all_records if r['order_type'] == 'MARKET'),
            'limit_orders': sum(1 for r in all_records if r['order_type'] == 'LIMIT_IOC')
        }
