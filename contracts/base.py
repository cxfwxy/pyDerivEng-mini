"""
合约基类
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass
class Contract(ABC):
    trade_id: str     # 合约交易ID
    underlying: str   # 标的资产
    notional: float   # 名义本金
    trade_date: date  # 合约交易日期
    maturity: date    # 合约到期日

    @abstractmethod
    def contract_type(self) -> str:
        """
        返回合约类型字符串
        """
        ...

    def time_to_maturity(self, valuation_date: date) -> float:
        """
        返回剩余到期时间（年化），用于定价器计算折现因子
        """
        return max((self.maturity - valuation_date).days, 0) / 365.0
