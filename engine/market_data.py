"""
行情数据模块
"""
from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import Dict, List, Optional
from .events import MarketDataEvent
from .event_bus import EventBus
import numpy as np


@dataclass
class MarketSnapshot:
    as_of: date
    underlying: str
    spot: float
    vol: float
    rate: float
    div_yield: float

    def bumped(self, spot_mult: float = 1.0, vol_add: float = 0.0,
               rate_add: float = 0.0) -> "MarketSnapshot":
        """用于 Greeks / 情景分析"""
        return replace(
            self,
            spot=self.spot * spot_mult,
            vol=max(self.vol + vol_add, 1e-6),
            rate=self.rate + rate_add,
        )


class MarketDataService:
    def __init__(self, event_bus: Optional[EventBus] = None):
        self._snapshots: Dict[str, MarketSnapshot] = {}
        self._event_bus = event_bus

    def update(self, snapshot: MarketSnapshot) -> None:
        self._snapshots[snapshot.underlying] = snapshot
        if self._event_bus is not None:
            self._event_bus.publish(MarketDataEvent(
                as_of=snapshot.as_of,
                underlying=snapshot.underlying,
                spot=snapshot.spot,
                vol=snapshot.vol,
                rate=snapshot.rate,
                div_yield=snapshot.div_yield,
            ))


    def get(self, underlying: str) -> MarketSnapshot:
        return self._snapshots[underlying]


    @staticmethod
    def generate_gbm_path(snapshot: MarketSnapshot, n_days: int,
                           seed: Optional[int] = None) -> List[MarketSnapshot]:
        """模拟生成一条逐日行情路径（几何布朗运动），用于雪球的事件驱动演示"""
        rng = np.random.default_rng(seed)
        dt = 1.0 / 252.0
        drift = (snapshot.rate - snapshot.div_yield - 0.5 * snapshot.vol ** 2) * dt
        diffusion = snapshot.vol * np.sqrt(dt)
        z = rng.standard_normal(n_days)
        log_returns = drift + diffusion * z
        spots = snapshot.spot * np.exp(np.cumsum(log_returns))

        path = []
        cur_date = snapshot.as_of
        for i in range(n_days):
            cur_date = cur_date + timedelta(days=1)
            path.append(MarketSnapshot(
                as_of=cur_date,
                underlying=snapshot.underlying,
                spot=float(spots[i]),
                vol=snapshot.vol,
                rate=snapshot.rate,
                div_yield=snapshot.div_yield,
            ))
        return path
