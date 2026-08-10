"""
雪球期权（Snowball）
--------------------------------
条款：
  - initial_fixing      : 期初标的价格
  - coupon_rate         : 票息（年化）
  - ki_barrier          : 敲入线
  - ko_barrier          : 敲出线
  - ko_lock_months      : 敲出观察锁定期（前 N 个月不观察敲出）
  - obs_freq_months     : 敲出观察频率（通常每月一次）

Payoff 规则：
  1) 存续期内任一敲出观察日 S >= ko_barrier * S0  =>  敲出，
     投资人获得 本金 * (1 + coupon_rate * elapsed_years)，合约提前终止
  2) 若从未敲出，存续到期：
       a) 从未触碰敲入线（S 始终 > ki_barrier*S0）=> 获得全额票息:
          本金 * (1 + coupon_rate * total_years)
       b) 曾经敲入，但期末价格 >= 期初价格 => 仅返还本金，无票息
       c) 曾经敲入，且期末价格 < 期初价格   => 本金 * (S_T / S0)（承担下跌敞口，类似空put）
"""
from dataclasses import dataclass
from datetime import date
from typing import List
from dateutil.relativedelta import relativedelta
from .base import Contract


@dataclass
class SnowballOption(Contract):
    initial_fixing: float = 0.0
    ko_barrier: float = 1.03
    ki_barrier: float = 0.75
    coupon_rate: float = 0.15
    ko_lock_months: int = 3
    obs_freq_months: int = 1

    def contract_type(self) -> str:
        """返回合约类型字符串"""
        return "SnowballOption"

    def ko_observation_dates(self) -> List[date]:
        """生成敲出观察日列表（锁定期后，按月观察，直到到期）"""
        dates = []
        d = self.trade_date + relativedelta(months=self.ko_lock_months)
        while d <= self.maturity:
            dates.append(d)
            d += relativedelta(months=self.obs_freq_months)
        return dates

    def ko_barrier_level(self) -> float:
        return self.ko_barrier * self.initial_fixing

    def ki_barrier_level(self) -> float:
        return self.ki_barrier * self.initial_fixing

    def elapsed_years(self, as_of: date) -> float:
        """计算从合约交易日到敲出日的年化时间"""
        return max((as_of - self.trade_date).days, 0) / 365.0

    def payoff_at_knockout(self, ko_date: date) -> float:
        """计算敲出时的现金流金额（本金 + 票息）"""
        return self.notional * (1.0 + self.coupon_rate * self.elapsed_years(ko_date))

    def payoff_at_maturity(self, final_spot: float, ever_knocked_in: bool) -> float:
        """计算到期时的现金流金额"""
        total_years = self.elapsed_years(self.maturity)
        if not ever_knocked_in:
            return self.notional * (1.0 + self.coupon_rate * total_years)
        if final_spot >= self.initial_fixing:
            return self.notional
        return self.notional * (final_spot / self.initial_fixing)

    def payoff_paths(self, paths, obs_step_indices):
        """
        MC方法使用，对一批模拟路径同时定价
        paths: ndarray, shape (n_paths, n_steps+1)，包含t0在内的每日模拟价格
        obs_step_indices: 敲出观察日对应的“步数索引”（int array）

        返回: (discounted-free) 每条路径的到期/敲出现金流 与 对应的实现年限（用于折现）
        """
        import numpy as np
        n_paths, n_steps_plus_1 = paths.shape # n_paths模拟路径数量, n_steps_plus_1每一个时间步（包含t0）
        payouts = np.zeros(n_paths) # 每条路径最终获得的现金流金额（未折现）
        pay_years = np.zeros(n_paths) # 每条路径现金流发生的对应时间点（以年为单位）
        knocked_out = np.zeros(n_paths, dtype=bool) # 记录每条路径是否已敲出

        ko_level = self.ko_barrier_level()
        ki_level = self.ki_barrier_level()
        total_years = self.elapsed_years(self.maturity)
        dt_years = total_years / (n_steps_plus_1 - 1)

        # 1) 逐个敲出观察日检查
        for idx in obs_step_indices:
            still_alive = ~knocked_out # 当前仍存续的路径
            hit = still_alive & (paths[:, idx] >= ko_level) # 检查是否触碰敲出线
            payouts[hit] = self.notional * (1.0 + self.coupon_rate * idx * dt_years) # 计算敲出时的现金流金额（本金 + 票息）
            pay_years[hit] = idx * dt_years # 计算敲出时的年化时间
            knocked_out |= hit # 标记已敲出的路径，已敲出的继续保持已敲出

        # 2) 未敲出的路径，检查是否敲入 + 期末价格
        alive = ~knocked_out # 当前仍存续的路径
        ever_ki = (paths[:, 1:].min(axis=1) <= ki_level)  # 全程（不含t0）最低点是否触碰敲入线
        final_spot = paths[:, -1] # 每条路径的期末价格

        no_ki_mask = alive & (~ever_ki) # 未敲出且从未敲入的路径
        payouts[no_ki_mask] = self.notional * (1.0 + self.coupon_rate * total_years) # 全额票息

        ki_up_mask = alive & ever_ki & (final_spot >= self.initial_fixing) # 敲入过但期末价格 >= 期初价格的路径
        payouts[ki_up_mask] = self.notional # 仅返还本金

        ki_down_mask = alive & ever_ki & (final_spot < self.initial_fixing) # 敲入过且期末价格 < 期初价格的路径
        payouts[ki_down_mask] = self.notional * (final_spot[ki_down_mask] / self.initial_fixing) # 返还本金 * (S_T / S0)

        pay_years[alive] = total_years # 计算到期时的年化时间
        return payouts, pay_years # 返回每条路径的现金流金额和对应的年化时间
