"""
蒙特卡洛定价器 —— CPU（numpy 向量化）实现
--------------------------------
支持：
  EuropeanOption、SnowballOption（按月观察敲出 + 逐日监控敲入）
"""
import math
import numpy as np
from contracts.european_option import EuropeanOption
from contracts.snowball import SnowballOption
from .base import PricerBase, PricingResult


class MonteCarloCPUPricer(PricerBase):
    name = "MC-CPU"

    def __init__(self, n_paths: int = 200_000, n_steps_per_year: int = 252, seed: int = 42):
        self.n_paths = n_paths
        self.n_steps_per_year = n_steps_per_year
        self.seed = seed

    def price(self, contract, market) -> PricingResult:
        ctype = contract.contract_type()
        if ctype == "EuropeanOption":
            return self._price_european(contract, market)
        elif ctype == "SnowballOption":
            return self._price_snowball(contract, market)
        raise TypeError(f"MC定价方法不支持合约类型: {ctype}")

    def _draw_normals(self, n_paths, n_steps, rng):
        """使用对偶变量法降低方差"""
        half = (n_paths + 1) // 2
        z = rng.standard_normal((half, n_steps))
        return np.concatenate([z, -z], axis=0)[:n_paths]

    def simulate_paths(self, S0, r, q, sigma, T, n_steps, n_paths=None, seed=None):
        """生成几何布朗运动路径，返回 shape (n_paths, n_steps+1)，含t0在内"""
        n_paths = n_paths or self.n_paths
        rng = np.random.default_rng(seed if seed is not None else self.seed)
        dt = T / n_steps
        z = self._draw_normals(n_paths, n_steps, rng)
        drift = (r - q - 0.5 * sigma ** 2) * dt
        diffusion = sigma * math.sqrt(dt) * z
        log_paths = np.cumsum(drift + diffusion, axis=1)
        paths = S0 * np.exp(log_paths)
        paths = np.concatenate([np.full((n_paths, 1), S0), paths], axis=1)
        return paths

    def _price_european(self, contract: EuropeanOption, market) -> PricingResult:
        """模拟欧式期权"""
        S0 = market.spot
        r = market.rate
        q = market.div_yield
        sigma = market.vol
        T = contract.time_to_maturity(market.as_of)
        if T <= 0:
            # 到期时直接计算内在价值
            return PricingResult(contract.payoff(S0) * contract.notional, self.name, {"T": 0})

        rng = np.random.default_rng(self.seed)
        z = self._draw_normals(self.n_paths, 1, rng)[:, 0]
        ST = S0 * np.exp((r - q - 0.5 * sigma ** 2) * T + sigma * math.sqrt(T) * z)
        payoffs = contract.payoff_vectorized(ST) # 向量化计算每条路径的期末现金流
        discounted = math.exp(-r * T) * payoffs  # 折现到当前时刻
        price = discounted.mean() * contract.notional # 平均值乘以名义本金
        stderr = discounted.std(ddof=1) / math.sqrt(self.n_paths) * contract.notional # 标准误差
        return PricingResult(price, self.name, {"T": T, "stderr": stderr, "n_paths": self.n_paths})

    def _price_snowball(self, contract: SnowballOption, market) -> PricingResult:
        r = market.rate
        q = market.div_yield
        sigma = market.vol
        T = contract.time_to_maturity(market.as_of)
        if T <= 0:
            # 到期时直接计算现金流
            return PricingResult(0.0, self.name, {"T": 0})

        n_steps = max(int(round(T * self.n_steps_per_year)), 1)
        paths = self.simulate_paths(market.spot, r, q, sigma, T, n_steps, seed=self.seed)

        # 把敲出观察日映射到路径步数索引
        obs_dates = contract.ko_observation_dates()
        obs_indices = [
            min(max(int(round((d - contract.trade_date).days / (T * 365.0) * n_steps)), 1), n_steps)
            for d in obs_dates
        ]

        payouts, pay_years = contract.payoff_paths(paths, obs_indices) # 计算每条路径的现金流金额和对应的年化时间
        discounted = payouts * np.exp(-r * pay_years) # 折现到当前时刻
        price = float(discounted.mean()) # 平均值作为定价结果，雪球内部已考虑了名义本金
        stderr = float(discounted.std(ddof=1) / math.sqrt(len(discounted)))
        return PricingResult(price, self.name, {"T": T, "stderr": stderr, "n_paths": self.n_paths, "n_steps": n_steps})
