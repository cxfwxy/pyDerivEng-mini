"""
簿记管理
--------------------------------
功能：
  1. 持仓管理
  2. 估值
  3. 记账：订阅 SettlementEvent/KnockOutEvent/MaturityEvent进行处理
"""
from typing import Dict, Optional
import pandas as pd
from engine.event_bus import EventBus
from engine.events import KnockOutEvent, MaturityEvent, SettlementEvent
from .position import Position, PositionStatus


class Portfolio:
    def __init__(self, name: str, event_bus: Optional[EventBus] = None,
                 pricers: Optional[Dict[str, object]] = None):
        self.name = name
        self.positions: Dict[str, Position] = {}
        self.cash_balance: float = 0.0  # 现金余额（记账用，T+1结算后才会入账）
        self.settlement_log = []  # 记录每笔结算事件的明细
        self.pricers = pricers or {}   # contract_type -> pricer 实例

        if event_bus is not None:
            event_bus.subscribe(KnockOutEvent, self._on_knock_out)
            event_bus.subscribe(MaturityEvent, self._on_maturity)
            event_bus.subscribe(SettlementEvent, self._on_settlement)

    def add_position(self, position: Position) -> None:
        self.positions[position.trade_id] = position

    def get_position(self, trade_id: str) -> Position:
        return self.positions[trade_id]

    def mark_to_market(self, market_data_service) -> pd.DataFrame:
        rows = []
        for trade_id, pos in self.positions.items():
            if pos.status != PositionStatus.OPEN:
                continue
            contract = pos.contract
            pricer = self.pricers.get(contract.contract_type())
            if pricer is None:
                continue
            market = market_data_service.get(contract.underlying)
            result = pricer.price(contract, market)
            rows.append({
                "trade_id": trade_id,
                "contract_type": contract.contract_type(),
                "underlying": contract.underlying,
                "quantity": pos.quantity,
                "price_per_unit": result.price,
                "pv": result.price * pos.quantity,
                "method": result.method,
            })
        df = pd.DataFrame(rows)
        return df

    def _on_knock_out(self, event: KnockOutEvent) -> None:
        """敲出事件处理：标记持仓状态为KNOCKED_OUT"""
        if event.trade_id in self.positions:
            self.positions[event.trade_id].status = PositionStatus.KNOCKED_OUT

    def _on_maturity(self, event: MaturityEvent) -> None:
        """到期事件处理：标记持仓状态为MATURED"""
        if event.trade_id in self.positions:
            self.positions[event.trade_id].status = PositionStatus.MATURED

    def _on_settlement(self, event: SettlementEvent) -> None:
        """结算事件处理：现金入账，更新持仓的realized_pnl"""
        if event.trade_id not in self.positions:
            return
        pos = self.positions[event.trade_id]
        cash_in = event.amount * pos.quantity
        self.cash_balance += cash_in
        pos.realized_pnl += cash_in
        self.settlement_log.append({
            "trade_id": event.trade_id,
            "settle_date": event.settle_date,
            "amount": cash_in,
            "description": event.description,
        })

    def summary(self) -> pd.DataFrame:
        """组合持仓状态汇总"""
        rows = [{
            "trade_id": tid,
            "contract_type": pos.contract.contract_type(),
            "status": pos.status.value,
            "quantity": pos.quantity,
            "realized_pnl": pos.realized_pnl,
        } for tid, pos in self.positions.items()]
        return pd.DataFrame(rows)
