"""
测试：BS对同一份欧式期权定价结果应互相收敛
"""
from datetime import date
from engine.market_data import MarketSnapshot
from contracts.european_option import EuropeanOption
from pricers.bs_pricer import BlackScholesPricer
from pricers.pde_pricer import PDEPricer
from pricers.mc_pricer_cpu import MonteCarloCPUPricer


def make_market():
    return MarketSnapshot(as_of=date(2024, 4, 1), underlying="TEST",
                           spot=100.0, vol=0.20, rate=0.03, div_yield=0.01)


def make_call():
    return EuropeanOption(trade_id="T1", underlying="TEST", notional=1.0,
                           trade_date=date(2024, 4, 1), maturity=date(2026, 4, 2),
                           strike=100.0, option_type="call")


def make_put():
    return EuropeanOption(trade_id="T2", underlying="TEST", notional=1.0,
                           trade_date=date(2024, 4, 1), maturity=date(2026, 4, 2),
                           strike=100.0, option_type="put")


def test_put_call_parity_bs():
    market= make_market()
    call= make_call()
    put = make_put()
    pricer = BlackScholesPricer()
    c = pricer.price(call, market).price
    p = pricer.price(put, market).price
    T = call.time_to_maturity(market.as_of)
    import math
    lhs = c - p
    rhs = market.spot * math.exp(-market.div_yield * T) - call.strike * math.exp(-market.rate * T)
    assert abs(lhs - rhs) < 1e-6


def test_pde_match_bs_call():
    market = make_market()
    call = make_call()
    bs_price = BlackScholesPricer().price(call, market).price
    pde_price = PDEPricer(n_space=300, n_time=300).price(call, market).price
    assert abs(bs_price - pde_price) < 0.05, (bs_price, pde_price)


def test_pde_match_bs_put():
    market = make_market()
    put = make_put()
    bs_price = BlackScholesPricer().price(put, market).price
    pde_price = PDEPricer(n_space=300, n_time=300).price(put, market).price
    assert abs(bs_price - pde_price) < 0.05, (bs_price, pde_price)


def test_mc_matches_bs_within_confidence_interval():
    market, call = make_market(), make_call()
    bs_price = BlackScholesPricer().price(call, market).price
    mc_result = MonteCarloCPUPricer(n_paths=300_000, seed=1).price(call, market)
    diff = abs(bs_price - mc_result.price)
    assert diff < 4 * mc_result.extra["stderr"], (bs_price, mc_result.price, mc_result.extra["stderr"])