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
        return tuple((item.value, item.translate) for item in cls if item not in excludes)


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
