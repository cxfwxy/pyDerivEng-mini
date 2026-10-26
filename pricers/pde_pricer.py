"""
有限差分（Crank-Nicolson）PDE 定价器（仅支持欧式期权）
"""
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from contracts.european_option import EuropeanOption
from .base import PricerBase, PricingResult


class PDEPricer(PricerBase):
    name = "PDE"

    def __init__(self, n_space: int = 200, n_time: int = 200, s_max_mult: float = 3.0):
        self.n_space = n_space
        self.n_time = n_time
        self.s_max_mult = s_max_mult

    def price(self, contract: EuropeanOption, market) -> PricingResult:
        if contract.contract_type() != "EuropeanOption":
            raise TypeError("PDEPricer 仅支持 EuropeanOption")

        S0, K = market.spot, contract.strike
        r, q, sigma = market.rate, market.div_yield, market.vol
        T = contract.time_to_maturity(market.as_of)
        is_call = contract.option_type == "call"

        if T <= 0:
            return PricingResult(contract.payoff(S0) * contract.notional, self.name, {"T": 0.0})

        M, N = self.n_space, self.n_time
        Smax = self.s_max_mult * max(S0, K)
        dS = Smax / M
        dt = T / N
        S = np.linspace(0.0, Smax, M + 1)

        V = np.maximum(S - K, 0.0) if is_call else np.maximum(K - S, 0.0)

        j = np.arange(1, M)
        sigma2 = sigma ** 2
        a = 0.25 * dt * (sigma2 * j ** 2 - (r - q) * j)
        b = -0.5 * dt * (sigma2 * j ** 2 + r)
        c = 0.25 * dt * (sigma2 * j ** 2 + (r - q) * j)

        M1 = sp.diags([-a[1:], 1 - b, -c[:-1]], offsets=[-1, 0, 1], format="csc")
        M2 = sp.diags([a[1:], 1 + b, c[:-1]], offsets=[-1, 0, 1], format="csc")
        lu = spla.splu(M1)

        def boundary(tau):
            if is_call:
                v0 = 0.0
                vM = Smax * np.exp(-q * tau) - K * np.exp(-r * tau)
            else:
                v0 = K * np.exp(-r * tau)
                vM = 0.0
            return v0, vM

        tau_old = 0.0
        for n in range(N):
            tau_new = (n + 1) * dt
            v0_old, vM_old = boundary(tau_old)
            v0_new, vM_new = boundary(tau_new)

            rhs = M2.dot(V[1:M])
            rhs[0] += a[0] * (v0_old + v0_new)
            rhs[-1] += c[-1] * (vM_old + vM_new)

            V_inner = lu.solve(rhs)
            V = np.concatenate(([v0_new], V_inner, [vM_new]))
            tau_old = tau_new

        price = float(np.interp(S0, S, V))
        return PricingResult(price * contract.notional, self.name, {"T": T, "grid": (M, N)})
