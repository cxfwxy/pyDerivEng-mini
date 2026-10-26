"""
测试：雪球合约 payoff 逻辑 + MC 定价
"""
from datetime import date
from engine.market_data import MarketSnapshot
from contracts.snowball import SnowballOption
from pricers.mc_pricer_cpu import MonteCarloCPUPricer


def make_snowball():
    return SnowballOption(
        trade_id="SB1", underlying="TEST", notional=1_000_000.0,
        trade_date=date(2024, 1, 2), maturity=date(2025, 1, 2),
        initial_fixing=100.0, ko_barrier=1.03, ki_barrier=0.75,
        coupon_rate=0.18, ko_lock_months=3, obs_freq_months=1,
    )


# 测试雪球到期不曾敲入
def test_maturity_payoff_no_knocked_in():
    sb = make_snowball()
    payoff = sb.payoff_at_maturity(final_spot=105.0, ever_knocked_in=False)
    expected = sb.notional * (1 + sb.coupon_rate * sb.elapsed_years(sb.maturity))
    assert abs(payoff - expected) < 1e-6


# 测试雪球到期曾敲入且最终下跌，损失本金
def test_maturity_payoff_knocked_in_and_down_loses_principal():
    sb = make_snowball()
    payoff = sb.payoff_at_maturity(final_spot=60.0, ever_knocked_in=True)
    assert payoff == sb.notional * 0.6
    assert payoff < sb.notional


# 测试雪球到期曾敲入但最终上涨，仍然只返还本金
def test_maturity_payoff_knocked_in_but_recovered_returns_principal_only():
    sb = make_snowball()
    payoff = sb.payoff_at_maturity(final_spot=101.0, ever_knocked_in=True)
    assert payoff == sb.notional


# 测试雪球敲出观察日期是否遵守锁定期
def test_ko_observation_dates_respect_lock_period():
    sb = make_snowball()
    dates = sb.ko_observation_dates()
    assert dates[0] == date(2024, 4, 2)  # trade_date + 3 months lock
    assert dates[-1] <= sb.maturity


# 测试雪球 MC 定价是否合理
def test_mc_snowball_price_is_positive_and_reasonable():
    sb = make_snowball()
    market = MarketSnapshot(as_of=date(2024, 1, 2), underlying="TEST",
                             spot=100.0, vol=0.22, rate=0.02, div_yield=0.0)
    result = MonteCarloCPUPricer(n_paths=50_000, seed=5).price(sb, market)
    # 雪球期权定价通常在本金附近波动（含票息补偿 vs 尾部下跌风险）
    assert 0.5 * sb.notional < result.price < 1.3 * sb.notional
