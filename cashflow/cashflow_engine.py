"""
现金流引擎
--------------------------------
功能：把“业务事件”（敲入/敲出/到期）转换成“现金流事件”，再转换成“结算事件”。

流程：
    KnockOutEvent  ----\
    KnockInEvent   ----- CashflowEngine ----> CashflowEvent ----> SettlementEvent
    MaturityEvent  ----/                        (T+1 结算)
"""
from datetime import timedelta
from typing import Dict
from engine.event_bus import EventBus
from engine.events import (
    KnockInEvent, KnockOutEvent, MaturityEvent, CashflowEvent, SettlementEvent,
)
from contracts.snowball import SnowballOption


SETTLEMENT_LAG_DAYS = 1  # T+1 结算，简化处理

class CashflowEngine:
    def __init__(self, event_bus: EventBus, contracts: Dict[str, SnowballOption]):
        self.event_bus = event_bus  # 事件总线
        self.contracts = contracts  # 合约的trade_id
        self._knocked_in: Dict[str, bool] = {tid: False for tid in contracts}  # 记录每个合约是否曾经敲入过，初始值全为false

        event_bus.subscribe(KnockInEvent, self._on_knock_in)    # 订阅敲入事件
        event_bus.subscribe(KnockOutEvent, self._on_knock_out)  # 订阅敲出事件
        event_bus.subscribe(MaturityEvent, self._on_maturity)   # 订阅到期事件

    def _on_knock_in(self, event: KnockInEvent) -> None:
        # 敲入事件只记录状态，不触发现金流
        self._knocked_in[event.trade_id] = True  # 标记该合约已敲入

    def _on_knock_out(self, event: KnockOutEvent) -> None:
        # 敲出事件触发现金流结算
        contract = self.contracts[event.trade_id] # 获取合约对象
        amount = contract.payoff_at_knockout(event.obs_date) # 计算敲出时的现金流金额
        self._emit_cashflow(event.trade_id, event.obs_date, amount, f"敲出结算 @ {event.obs_date} spot={event.spot:.2f}") # 发出现金流事件

    def _on_maturity(self, event: MaturityEvent) -> None:
        # 到期事件触发现金流结算
        contract = self.contracts[event.trade_id] # 获取合约对象
        ever_ki = self._knocked_in.get(event.trade_id, False) # 检查该合约是否曾经敲入过
        amount = contract.payoff_at_maturity(event.spot, ever_ki) # 计算到期时的现金流金额
        tag = "敲入未敲出" if ever_ki else "从未敲入(全额票息)" # 生成结算标签
        self._emit_cashflow(event.trade_id, event.obs_date, amount, f"到期结算({tag}) @ {event.obs_date} spot={event.spot:.2f}") # 发出现金流事件

    def _emit_cashflow(self, trade_id, pay_date, amount, description) -> None:
        # 发出现金流事件和结算事件
        self.event_bus.publish(CashflowEvent(trade_id=trade_id, pay_date=pay_date, amount=amount, description=description)) # 发出现金流事件
        settle_date = pay_date + timedelta(days=SETTLEMENT_LAG_DAYS) # 计算结算日期，T+1结算
        self.event_bus.publish(SettlementEvent(trade_id=trade_id, settle_date=settle_date, amount=amount, description=description)) # 发出结算事件
