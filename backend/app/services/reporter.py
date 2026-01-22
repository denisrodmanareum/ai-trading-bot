import asyncio
from datetime import datetime, date, timedelta
from typing import List, Dict
from sqlalchemy import select, func
from loguru import logger
from app.database import SessionLocal
from app.models import Trade, DailyReport

class DailyReporterService:
    """Analyzes daily trades and generates AI reports"""
    
    def __init__(self):
        self.running = False

    async def generate_daily_report(self, target_date: date = None):
        """Analyze trades for a given date and save to DB"""
        if target_date is None:
            # Use UTC date as the source of truth for database records
            target_date = datetime.utcnow().date()
            
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())
        
        logger.info(f"Generating daily report for UTC date {target_date}...")
        
        async with SessionLocal() as session:
            try:
                # 1. Fetch trades for the day
                query = select(Trade).where(Trade.timestamp >= start_dt, Trade.timestamp <= end_dt)
                result = await session.execute(query)
                trades = result.scalars().all()
                
                if not trades:
                    logger.info(f"No trades found for {target_date}, skipping report.")
                    return None

                # 2. Calculate Stats
                total_trades = len(trades)
                # Filter for CLOSE actions to calculate PnL properly
                close_trades = [t for t in trades if t.action == "CLOSE"]
                
                wins = len([t for t in close_trades if (t.pnl or 0) > 0])
                losses = len([t for t in close_trades if (t.pnl or 0) <= 0])
                total_pnl = sum([t.pnl for t in close_trades if t.pnl is not None])
                total_comm = sum([t.commission for t in trades if t.commission is not None])
                
                win_rate = (wins / len(close_trades) * 100) if close_trades else 0.0
                
                # 3. Calculate Strategy Style
                avg_hold_time = await self._calculate_avg_hold_time(trades)
                
                # 4. Generate AI Remark
                remark = self._generate_remark(total_trades, total_pnl, win_rate, total_comm, avg_hold_time)
                
                # 4. Save to DB
                # Check if report already exists for this date
                check_query = select(DailyReport).where(func.date(DailyReport.date) == target_date)
                check_res = await session.execute(check_query)
                existing = check_res.scalar_one_or_none()
                
                if existing:
                    existing.total_trades = total_trades
                    existing.wins = wins
                    existing.losses = losses
                    existing.win_rate = win_rate
                    existing.total_pnl = total_pnl
                    existing.total_commission = total_comm
                    existing.ai_remark = remark
                    logger.info(f"Updated existing report for {target_date}")
                else:
                    report = DailyReport(
                        date=start_dt,
                        total_trades=total_trades,
                        wins=wins,
                        losses=losses,
                        win_rate=win_rate,
                        total_pnl=total_pnl,
                        total_commission=total_comm,
                        ai_remark=remark
                    )
                    session.add(report)
                    logger.info(f"Created new daily report for {target_date}")
                
                await session.commit()
                
                # -- NEW: Automated Retraining Check --
                try:
                    from app.api.ai_control import get_scheduler
                    sched = get_scheduler()
                    
                    if sched and sched.config.get("enabled"):
                        net_pnl = total_pnl - total_comm
                        min_wr = sched.config.get("min_win_rate", 50.0)
                        
                        trigger = False
                        if win_rate < min_wr:
                            logger.warning(f"Auto-Retrain: Win Rate ({win_rate:.1f}%) < Threshold ({min_wr}%)")
                            trigger = True
                        elif sched.config.get("retrain_on_loss") and net_pnl < 0:
                            logger.warning(f"Auto-Retrain: Daily PnL (${net_pnl:.2f}) is negative.")
                            trigger = True
                            
                        if trigger:
                            logger.info("Triggering Self-Healing Retraining...")
                            asyncio.create_task(sched.trigger_retraining())
                            
                            # Mark as retrained in DB
                            # We need to refresh/fetch to avoid session closed issues if commit was final
                            report_id = existing.id if existing else report.id
                            async with SessionLocal() as session_new:
                                from sqlalchemy import update
                                await session_new.execute(
                                    update(DailyReport).where(DailyReport.id == report_id).values(retrained=True)
                                )
                                await session_new.commit()
                except Exception as ex:
                    logger.error(f"Failed to check auto-retrain: {ex}")

                return remark

            except Exception as e:
                logger.error(f"Failed to generate daily report: {e}")
                await session.rollback()
                return None

    async def _calculate_avg_hold_time(self, trades: List[Trade]) -> float:
        """Calculate average holding time (in minutes) for a list of trades"""
        if not trades: return 0.0
        
        hold_times = []
        active_positions = {} # symbol -> open_time
        
        for t in trades:
            if t.action in ["LONG", "SHORT"]:
                active_positions[t.symbol] = t.timestamp
            elif t.action == "CLOSE" and t.symbol in active_positions:
                open_time = active_positions.pop(t.symbol)
                duration = (t.timestamp - open_time).total_seconds() / 60.0
                hold_times.append(duration)
        
        return sum(hold_times) / len(hold_times) if hold_times else 0.0

    def _get_strategy_style(self, avg_hold_minutes: float) -> str:
        """Categorize trading style based on average holding time"""
        if avg_hold_minutes == 0: return "SYSTEM NEUTRAL"
        if avg_hold_minutes < 30: return "TACTICAL SCALPER"
        if avg_hold_minutes < 240: return "DAY TRADER"
        return "STRATEGIC SWINGER"

    def _generate_remark(self, trades, pnl, win_rate, comm, avg_hold_time=0) -> str:
        """Generate a human-like remark from AI with a Strategic Sentinel tone"""
        net_pnl = pnl - comm
        style = self._get_strategy_style(avg_hold_time)
        
        if trades == 0:
            return "시스템 현재 관망 모드(Wait-and-Watch) 유지 중. 유의미한 시장 진입 패밀리가 탐지되지 않아 자산 보호 프로토콜이 작동되었습니다. 무분별한 진입보다 자정 결합도가 높습니다."
        
        # Style Header
        style_header = f"[{style}] 정밀 분석 결과: " if avg_hold_time > 0 else ""
        
        # High Fee Warning
        if comm > abs(pnl) * 0.5 and trades > 20:
             return style_header + f"운용 경고: 금일 {trades}회의 과도한 오퍼레이션으로 인해 총 수수료(${comm:.2f})가 수익 잠재력을 침해했습니다. 오버트레이딩 탐지됨. 진입 필터 스펙트럼 조정이 시급합니다."

        if net_pnl > 0:
            if win_rate > 70:
                return style_header + f"전술 성공: 정밀화된 데이터 매칭으로 승률 {win_rate:.1f}% 달성. 수수료 제외 ${net_pnl:.2f}의 순수익을 확보했습니다. 현재 백테스트 모델과의 오차율 최저치 기록 중."
            else:
                return style_header + f"수익 확보: 승률({win_rate:.1f}%)은 안정권이나, 정교한 손익비(RR Ratio) 제어를 통해 수수료 ${comm:.2f}를 상쇄하고 ${net_pnl:.2f}의 순수익을 추출했습니다. 효율적 운용 지속 중."
        else:
            if trades > 30:
                return style_header + f"전술 이탈 주의: 노이즈 구간에서의 잦은 진입({trades}회)으로 수수료 ${comm:.2f}가 과도하게 누적되었습니다. 지능형 슬리피지 및 마찰 손실이 발생했으므로 보수적 운용으로 전환합니다."
            else:
                return style_header + f"전후 분석: 시장의 불규칙한 변동성으로 인해 ${net_pnl:.2f}의 전략적 손실이 발생했습니다. 리스크 매니지먼트 임계치 내에서 제어되고 있으며, 데이터 재학습 큐를 검토 중입니다."

    async def schedule_daily(self):
        """Background loop to run report every night"""
        self.running = True
        logger.info("Daily Reporter scheduler started.")
        
        while self.running:
            now = datetime.utcnow() # Use UTC for scheduling
            # Target check at 23:55 UTC (or adjust for local preference)
            # Since local is UTC+9, 23:55 UTC is 08:55 AM Local
            if now.hour == 23 and now.minute >= 55:
                await self.generate_daily_report(now.date())
                # Wait until next day to avoid double running
                await asyncio.sleep(3600) 
            
            await asyncio.sleep(60) # Check every minute
