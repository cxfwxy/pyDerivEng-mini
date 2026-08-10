"""
持仓（Position）
--------------------------------
一笔交易在簿记系统里的记账单元：合约条款 + 方向/数量 + 生命周期状态。
"""
from dataclasses import dataclass
from enum import Enum


class PositionStatus(Enum):
    OPEN = "OPEN"
    KNOCKED_OUT = "KNOCKED_OUT"
    MATURED = "MATURED"


@dataclass
class Position:
    contract: object          # EuropeanOption / SnowballOption
    quantity: float = 1.0     # +1 表示买入(持有多头)，-1 表示卖出
    status: PositionStatus = PositionStatus.OPEN
    realized_pnl: float = 0.0

    @property
    def trade_id(self) -> str:
        return self.contract.trade_id
