"""
Demo 入口
--------------------------------
运行: python run_demo.py

演示内容：
  A. 欧式期权：BS / PDE / MC-CPU 互相对照
  B. Greeks（bump-and-reprice，基于 BS 定价器）
  C. 情景分析 / 压力测试网格
  D. 雪球期权：MC-CPU 定价
  E. 事件驱动全链路：行情驱动 -> 敲入/敲出监控 -> 现金流引擎 -> 组合记账
"""
from datetime import date

import pandas as pd

from engine.event_bus import EventBus
from engine.market_data import MarketDataService, MarketSnapshot
from contracts.european_option import EuropeanOption
from contracts.snowball import SnowballOption
from pricers.bs_pricer import BlackScholesPricer
from pricers.pde_pricer import PDEPricer
from pricers.mc_pricer_cpu import MonteCarloCPUPricer
from risk.greeks import GreeksCalculator
from risk.scenario import ScenarioEngine, Scenario
from lifecycle.barrier_monitor import BarrierMonitor
from cashflow.cashflow_engine import CashflowEngine
from portfolio.portfolio import Portfolio
from portfolio.position import Position


UNDERLYING = "TEST"
pd.set_option("display.float_format", lambda x: f"{x:,.4f}")


def section(title: str):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


# ---------------------------------------------------------------------- #
def demo_european_pricing():
    section("A. 欧式期权定价对照：BS / PDE / MC-CPU")

    market = MarketSnapshot(as_of=date(2024, 4, 1), underlying=UNDERLYING,
                             spot=1000.0, vol=0.20, rate=0.02, div_yield=0.0)
    option = EuropeanOption(trade_id="EUR-CALL-001", underlying=UNDERLYING, notional=1.0,
                             trade_date=date(2024, 4, 2), maturity=date(2025, 4, 2),
                             strike=1200.0, option_type="call")

    bs = BlackScholesPricer()
    pde = PDEPricer(n_space=200, n_time=200)
    mc_cpu = MonteCarloCPUPricer(n_paths=200_000, seed=1)

    rows = []
    for pricer in (bs, pde, mc_cpu):
        result = pricer.price(option, market)
        rows.append({"method": result.method, "price": result.price,
                     "stderr": result.extra.get("stderr", "-")})
    print(pd.DataFrame(rows).to_string(index=False))
    return option, market, bs


# ---------------------------------------------------------------------- #
def demo_greeks(option, market, bs_pricer):
    section("B. Greeks（bump-and-reprice, 基于 BS 定价器）")
    calc = GreeksCalculator(bs_pricer)
    greeks = calc.compute(option, market)
    print(f"Delta: {greeks.delta:+.4f}")
    print(f"Gamma: {greeks.gamma:+.6f}")
    print(f"Vega : {greeks.vega:+.4f}  (每 1 vol point)")
    print(f"Theta: {greeks.theta:+.4f}  (每日)")
    print(f"Rho  : {greeks.rho:+.4f}  (每 1bp)")


# ---------------------------------------------------------------------- #
def demo_scenario(option, market, bs_pricer):
    section("C. 情景分析 / 压力测试")
    engine = ScenarioEngine(bs_pricer)

    named = [
        Scenario("现货 -10%", spot_mult=0.9),
        Scenario("现货 -5%", spot_mult=0.95),
        Scenario("现货 +5%", spot_mult=1.05),
        Scenario("现货 +10%", spot_mult=1.10),
        Scenario("波动率 +5vol", vol_add=0.05),
        Scenario("波动率 -5vol", vol_add=-0.05),
        Scenario("利率 +50bp", rate_add=0.005),
    ]
    df = engine.run_named_scenarios(option, market, named)
    print(df.to_string(index=False))

    print("\n压力测试网格 (行=现货冲击, 列=波动率冲击):")
    grid = engine.run_grid(option, market)
    print(grid.to_string())


# ---------------------------------------------------------------------- #
def demo_snowball_pricing():
    section("D. 雪球期权（Autocallable Snowball）定价：MC-CPU")

    market = MarketSnapshot(as_of=date(2024, 4, 2), underlying=UNDERLYING,
                             spot=100.0, vol=0.20, rate=0.02, div_yield=0.0)
    snowball = SnowballOption(
        trade_id="SNOWBALL-001", underlying=UNDERLYING, notional=1_000_000.0,
        trade_date=date(2024, 4, 2), maturity=date(2025, 4, 2),
        initial_fixing=100.0, ko_barrier=1.03, ki_barrier=0.75,
        coupon_rate=0.15, ko_lock_months=3, obs_freq_months=1,
    )

    mc_cpu = MonteCarloCPUPricer(n_paths=100_000, n_steps_per_year=252, seed=7)

    result = mc_cpu.price(snowball, market)
    print(f"[{result.method:10s}] price = {result.price:,.2f}  "
            f"(notional={snowball.notional:,.0f}, stderr={result.extra['stderr']:.2f})")
    return snowball, market


# ---------------------------------------------------------------------- #
def demo_event_driven_lifecycle(snowball: SnowballOption, initial_market: MarketSnapshot):
    section("E. 事件驱动全链路：行情 -> 敲入/敲出监控 -> 现金流 -> 组合记账")

    event_bus = EventBus()
    market_data_service = MarketDataService(event_bus)

    contracts = {snowball.trade_id: snowball}
    barrier_monitor = BarrierMonitor(event_bus, contracts)
    cashflow_engine = CashflowEngine(event_bus, contracts)

    portfolio = Portfolio("Delta-Hedge-Book", event_bus, pricers={})
    portfolio.add_position(Position(contract=snowball, quantity=1.0))

    # 逐日生成一条模拟路径，驱动整条事件链
    n_days = (snowball.maturity - snowball.trade_date).days
    path = MarketDataService.generate_gbm_path(initial_market, n_days, seed=123)

    for snap in path:
        market_data_service.update(snap)
        event_bus.run()  # 当天行情触发的所有下游事件（敲入/敲出/结算/记账）同步处理完

    print("关键生命周期事件：")
    for e in event_bus.history:
        if e.event_type in ("KNOCK_OUT", "KNOCK_IN", "MATURITY", "SETTLEMENT"):
            print(f"  [{e.event_type:10s}] {e}")

    print("\n组合持仓状态：")
    print(portfolio.summary().to_string(index=False))
    print(f"\n组合现金余额（已实现现金流汇总）: {portfolio.cash_balance:,.2f}")


# ---------------------------------------------------------------------- #
if __name__ == "__main__":
    option, market, bs_pricer = demo_european_pricing()
    demo_greeks(option, market, bs_pricer)
    demo_scenario(option, market, bs_pricer)
    snowball, snowball_market = demo_snowball_pricing()
    demo_event_driven_lifecycle(snowball, snowball_market)
