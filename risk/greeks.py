"""
Greeks 计算模块，对 market snapshot 做微小扰动后重新调用pricer.price()
"""
from dataclasses import dataclass, replace
from datetime import timedelta


@dataclass
class GreeksResult:
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float


class GreeksCalculator:
    def __init__(self, pricer, spot_bump: float = 0.01, vol_bump: float = 0.01,
                 rate_bump: float = 0.0001):
        self.pricer = pricer
        self.spot_bump = spot_bump   # 相对扰动，如 1%
        self.vol_bump = vol_bump     # 绝对扰动，如 1 vol point = 0.01
        self.rate_bump = rate_bump   # 绝对扰动，如 1bp = 0.0001

    def compute(self, contract, market) -> GreeksResult:
        base = self.pricer.price(contract, market).price

        up = market.bumped(spot_mult=1 + self.spot_bump)
        down = market.bumped(spot_mult=1 - self.spot_bump)
        p_up = self.pricer.price(contract, up).price
        p_down = self.pricer.price(contract, down).price
        dS = market.spot * self.spot_bump

        delta = (p_up - p_down) / (2 * dS)
        gamma = (p_up - 2 * base + p_down) / (dS ** 2)

        vol_up = market.bumped(vol_add=self.vol_bump)
        p_vol_up = self.pricer.price(contract, vol_up).price
        vega = (p_vol_up - base) / self.vol_bump * 0.01  # 每 1 vol point 的价格变动

        rate_up = market.bumped(rate_add=self.rate_bump)
        p_rate_up = self.pricer.price(contract, rate_up).price
        rho = (p_rate_up - base) / self.rate_bump * 0.0001  # 每 1bp 的价格变动

        market_1d = replace(market, as_of=market.as_of + timedelta(days=1))
        p_theta = self.pricer.price(contract, market_1d).price
        theta = p_theta - base

        return GreeksResult(delta=delta, gamma=gamma, vega=vega, theta=theta, rho=rho)
