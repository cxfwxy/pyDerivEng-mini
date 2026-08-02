"""
行情数据模块
"""
from dataclasses import dataclass
from datetime import date
from typing import Dict


@dataclass
class MarketSnapshot:
    as_of: date
    underlying: str
    spot: float
    vol: float
    rate: float
    div_yield: float


class MarketDataService:
    def __init__(self):
        self._snapshots: Dict[str, MarketSnapshot] = {}

    def update(self, snapshot: MarketSnapshot) -> None:
        self._snapshots[snapshot.underlying] = snapshot

    def get(self, underlying: str) -> MarketSnapshot:
        return self._snapshots[underlying]
