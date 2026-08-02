"""
Black-Scholes 解析解定价器（仅支持欧式期权）
"""
import math
from scipy.stats import norm
from contracts.european_option import EuropeanOption
from .base import PricerBase, PricingResult


class BlackScholesPricer(PricerBase):
    name = "BS"

    def price(self, contract: EuropeanOption, market) -> PricingResult:
        if contract.contract_type() != "EuropeanOption":
            raise TypeError("Black-Scholes解析解定价方法仅支持EuropeanOption")

        S = market.spot 
        K = contract.strike
        r = market.rate
        q = market.div_yield
        sigma = market.vol
        T = contract.time_to_maturity(market.as_of)

        if T <= 0:
            intrinsic = contract.payoff(S) * contract.notional # 到期时的内在价值
            return PricingResult(intrinsic, self.name, {"T": 0.0})

        # Black-Scholes公式
        # Call：C=S*exp(-qT)*N(d1) - K*exp(-rT)*N(d2)
        # Put： P=K*exp(-rT)*N(-d2) - S*exp(-qT)*N(-d1)
        d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)

        if contract.option_type == "call":
            price = S * math.exp(-q * T) * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
        else:
            price = K * math.exp(-r * T) * norm.cdf(-d2) - S * math.exp(-q * T) * norm.cdf(-d1)

        return PricingResult(price * contract.notional, self.name, {"d1": d1, "d2": d2, "T": T})
