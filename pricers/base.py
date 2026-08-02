"""
定价器接口
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class PricingResult:
    price: float
    method: str
    extra: Dict[str, Any] = field(default_factory=dict) # 备注信息


class PricerBase(ABC):
    name: str = "base"

    @abstractmethod
    def price(self, contract, market) -> PricingResult:
        ...
