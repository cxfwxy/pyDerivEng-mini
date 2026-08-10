"""
情景分析 / 压力测试模块
"""
from dataclasses import dataclass
from typing import List, Optional
import numpy as np
import pandas as pd


@dataclass
class Scenario:
    name: str
    spot_mult: float = 1.0
    vol_add: float = 0.0
    rate_add: float = 0.0


class ScenarioEngine:
    def __init__(self, pricer):
        self.pricer = pricer

    def run_named_scenarios(self, contract, market, scenarios: List[Scenario]) -> pd.DataFrame:
        base_price = self.pricer.price(contract, market).price
        rows = []
        for sc in scenarios:
            bumped_market = market.bumped(spot_mult=sc.spot_mult, vol_add=sc.vol_add, rate_add=sc.rate_add)
            price = self.pricer.price(contract, bumped_market).price
            rows.append({
                "scenario": sc.name,
                "spot": bumped_market.spot,
                "vol": bumped_market.vol,
                "rate": bumped_market.rate,
                "price": price,
                "pnl": price - base_price,
                "pnl_pct": (price - base_price) / base_price if base_price else np.nan,
            })
        return pd.DataFrame(rows)

    def run_grid(self, contract, market, spot_shocks: Optional[List[float]] = None,
                 vol_shocks: Optional[List[float]] = None) -> pd.DataFrame:
        spot_shocks = spot_shocks or [-0.2, -0.1, -0.05, 0.0, 0.05, 0.1, 0.2]
        vol_shocks = vol_shocks or [-0.05, -0.02, 0.0, 0.02, 0.05]

        records = []
        for ss in spot_shocks:
            for vs in vol_shocks:
                bumped_market = market.bumped(spot_mult=1 + ss, vol_add=vs)
                price = self.pricer.price(contract, bumped_market).price
                records.append({"spot_shock": ss, "vol_shock": vs, "price": price})
        df = pd.DataFrame(records)
        return df.pivot(index="spot_shock", columns="vol_shock", values="price")
