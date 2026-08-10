"""
敲入/敲出监控模块（Barrier Monitor）
--------------------------------
订阅 MarketDataEvent（每日行情），对组合里所有存续中的雪球头寸做：
  - 每日敲入监控：spot <= 敲入线 -> 发布 KnockInEvent
  - 敲出观察日监控：spot >= 敲出线 -> 发布 KnockOutEvent，并将头寸标记为终止
  - 到期日：若既未敲出也未到期终止 -> 发布 MaturityEvent
"""
from typing import Dict, Set
from engine.event_bus import EventBus
from engine.events import MarketDataEvent, KnockInEvent, KnockOutEvent, MaturityEvent
from contracts.snowball import SnowballOption


class BarrierMonitor:
    """敲入/敲出监控：订阅MarketDataEvent，发布 KnockIn/KnockOut/Maturity 事件"""
    def __init__(self, event_bus: EventBus, contracts: Dict[str, SnowballOption]):
        self.event_bus = event_bus
        self.contracts = contracts
        self._ko_dates: Dict[str, Set] = {tid: set(c.ko_observation_dates()) for tid, c in contracts.items()} # 记录每个合约的敲出观察日集合
        self._active: Dict[str, bool] = {tid: True for tid in contracts} # 记录每个合约是否仍然存续（未敲出/未到期）
        event_bus.subscribe(MarketDataEvent, self._on_market_data)

    def _on_market_data(self, event: MarketDataEvent) -> None:
        """处理每日行情事件，逐个检查组合里所有存续中的雪球头寸"""
        for trade_id, contract in self.contracts.items():
            if not self._active[trade_id]:
                continue
            if contract.underlying != event.underlying:
                continue
            spot = event.spot
            obs_date = event.as_of

            # 1) 敲出观察（敲出当天即使同时触碰敲入线，也按敲出处理）
            if obs_date in self._ko_dates[trade_id] and spot >= contract.ko_barrier_level():
                self._active[trade_id] = False
                self.event_bus.publish(KnockOutEvent(
                    trade_id=trade_id, obs_date=obs_date, spot=spot,
                    elapsed_years=contract.elapsed_years(obs_date),
                ))
                continue

            # 2) 敲入监控（逐日）
            if spot <= contract.ki_barrier_level():
                self.event_bus.publish(KnockInEvent(trade_id=trade_id, obs_date=obs_date, spot=spot))

            # 3) 到期
            if obs_date >= contract.maturity:
                self._active[trade_id] = False
                self.event_bus.publish(MaturityEvent(trade_id=trade_id, obs_date=obs_date, spot=spot))
