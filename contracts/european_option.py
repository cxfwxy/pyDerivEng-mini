"""
欧式期权合约
"""
from dataclasses import dataclass
from .base import Contract


@dataclass
class EuropeanOption(Contract):
    strike: float  # 行权价
    option_type: str = "call"  # 合约方向"call" or "put"

    def contract_type(self) -> str:
        # 返回合约类型字符串
        return "EuropeanOption"

    def payoff(self, spot: float) -> float:
        """计算欧式期权 payoff"""
        if self.option_type == "call":
            return max(spot - self.strike, 0.0) # 欧式看涨期权 payoff = max(S-K,0)
        elif self.option_type == "put":
            return max(self.strike - spot, 0.0) # 欧式看跌期权 payoff = max(K-S,0)
        raise ValueError(f"unknown option_type={self.option_type}") # 如果 option_type 不是 "call" 或 "put"，抛出异常

    def payoff_vectorized(self, spots):
        """向量化 payoff，供MC方法使用"""
        import numpy as np
        if self.option_type == "call":
            return np.maximum(spots - self.strike, 0.0) # 欧式看涨期权 payoff = max(S-K,0)
        elif self.option_type == "put":
            return np.maximum(self.strike - spots, 0.0) # 欧式看跌期权 payoff = max(K-S,0)
        raise ValueError(f"unknown option_type={self.option_type}") # 如果 option_type 不是 "call" 或 "put"，抛出异常
