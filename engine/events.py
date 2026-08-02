"""
事件定义模块
"""
from dataclasses import dataclass
from datetime import date


@dataclass
class Event:
    """所有事件的基类"""
    event_type: str = "EVENT"


@dataclass
class MarketDataEvent(Event):
    """行情快照事件"""
    as_of: date = None
    underlying: str = ""
    spot: float = 0.0
    vol: float = 0.0
    rate: float = 0.0
    div_yield: float = 0.0
    event_type: str = "MARKET_DATA"


@dataclass
class ObservationEvent(Event):
    """定期观察事件"""
    trade_id: str = ""
    obs_date: date = None
    spot: float = 0.0
    event_type: str = "OBSERVATION"


@dataclass
class KnockOutEvent(Event):
    """敲出事件：雪球在某个观察日 标的现价 >= 敲出线"""
    trade_id: str = ""
    obs_date: date = None
    spot: float = 0.0
    elapsed_years: float = 0.0
    event_type: str = "KNOCK_OUT"


@dataclass
class KnockInEvent(Event):
    """敲入事件：雪球在存续期内任一天 标的现价 <= 敲入线"""
    trade_id: str = ""
    obs_date: date = None
    spot: float = 0.0
    event_type: str = "KNOCK_IN"


@dataclass
class MaturityEvent(Event):
    """到期事件：雪球存续到 maturity 仍未敲出"""
    trade_id: str = ""
    obs_date: date = None
    spot: float = 0.0
    event_type: str = "MATURITY"
