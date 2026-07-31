import abc
from abc import ABC
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
