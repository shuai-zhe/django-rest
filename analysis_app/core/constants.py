from enum import Enum
from typing import Any


class ChoiceMixin(Enum):
    @property
    def translate(self):
        return self

    @classmethod
    def choices(cls, excludes=None) -> tuple[tuple[Any, Any], ...]:
        excludes = excludes or []
        return tuple(
            (item.value, item.translate) for item in cls if item not in excludes
        )

    # 返回所有name
    @classmethod
    def names(cls, excludes=None) -> tuple[str, ...]:
        excludes = excludes or []
        return tuple(item.name for item in cls if item not in excludes)

    # 返回所有value
    @classmethod
    def values(cls, excludes=None) -> tuple[str, ...]:
        excludes = excludes or []
        return tuple(item.value for item in cls if item not in excludes)

    @classmethod
    def value_to_self(cls, key):
        self = dict(zip(cls.values(), cls.names())).get(key)
        if not self:
            raise ValueError(f"未找到枚举值：{key}")
        return getattr(cls, self)


class ProjectStatus(ChoiceMixin):
    SPOT = "spot"
    FUTURES = "futures"

    @property
    def translate(self):
        map_ = {
            ProjectStatus.SPOT: "现货",
            ProjectStatus.FUTURES: "合约",
        }
        return map_[self]


class StockProjectStatus(ChoiceMixin):
    SPOT = "spot"

    @property
    def translate(self):
        map_ = {
            ProjectStatus.SPOT: "现货",
        }
        return map_[self]


class StockType(ChoiceMixin):
    SH = "sh"
    SZ = "sz"
    BJ = "bj"

    @property
    def translate(self):
        map_ = {
            StockType.SH: "上交所",
            StockType.SZ: "深交所",
            StockType.BJ: "北交所",
        }
        return map_[self]


class KlineInterval(ChoiceMixin):
    S1 = "1s"
    S10 = "10s"
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    H8 = "8h"
    D1 = "1d"
    D7 = "7d"
    D30 = "30d"

    def translate(self):
        map_ = {
            KlineInterval.S1: 1,
            KlineInterval.S10: 10,
            KlineInterval.M1: 60,
            KlineInterval.M5: 60 * 5,
            KlineInterval.M15: 60 * 15,
            KlineInterval.M30: 60 * 30,
            KlineInterval.H1: 60 * 60 * 1,
            KlineInterval.H4: 60 * 60 * 4,
            KlineInterval.H8: 60 * 60 * 8,
            KlineInterval.D1: 60 * 60 * 24,
            KlineInterval.D7: 60 * 60 * 24 * 7,
            KlineInterval.D30: 60 * 60 * 24 * 30,
        }

        return map_[self]

    def translate_to_future(self):
        map_ = {
            KlineInterval.M1: 1,
            KlineInterval.M5: 5,
            KlineInterval.M15: 15,
            KlineInterval.M30: 30,
            KlineInterval.H1: 60,
            KlineInterval.D1: "daily",
            KlineInterval.D7: "weekly",
            KlineInterval.D30: "monthly",
        }

        return map_[self]


class StockTrade(ChoiceMixin):
    BAOSTOCK = "baostock"
    AKSHARE = "akshare"

    @property
    def translate(self):
        map_ = {
            StockTrade.BAOSTOCK: "baostock",
            StockTrade.AKSHARE: "akshare",
        }
        return map_[self]


def time_interval_limit_builder(code):
    return {
        KlineInterval.M5.value: 6,
        KlineInterval.M15.value: 10 * 2,
        KlineInterval.M30.value: 33,
        KlineInterval.H1.value: 40 * 2,
        KlineInterval.D1.value: 200,
        KlineInterval.D7.value: 200,
        KlineInterval.D30.value: 400,
    }.get(code, 10)
