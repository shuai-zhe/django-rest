import abc

from apis.gate.default import _GetApi
from core.constants import KlineInterval
from core.utils import GetSetBuild


class BaseKlineBuild(metaclass=abc.ABCMeta):
    def __init__(self):
        self.params = {}

    @abc.abstractmethod
    def get_data(self, params, **kwargs) -> dict | list:
        pass

    def build_param(self, validated_data, **kwargs) -> dict | list:
        return validated_data

    def format(self, data, **kwargs) -> dict:
        return data

    def extra_format(self, data, **kwargs) -> dict:
        """额外的字段添加共同体中"""
        data["interval"] = list(KlineInterval.values())
        stop_interval = ["1s","10s"]
        for interval in stop_interval:
            if interval in data["interval"]:
                data["interval"].pop(data["interval"].index(interval))
        return data

    def build_kline(self, validated_data, **kwargs):
        self.params = self.build_param(validated_data, **kwargs)
        return self.format(self.get_data(self.params, **kwargs), **kwargs)

    def __call__(self, validated_data, **kwargs):
        return self.extra_format(self.build_kline(validated_data, **kwargs))


class GetKlineBuild(BaseKlineBuild):
    def get_data(self, params=None, **kwargs):
        _ = _GetApi.get_spot_kline(params)
        _.raise_for_status()
        return _.json()

    def build_param(self, validated_data, **kwargs):
        if not validated_data.get("code_id") or not validated_data.get("interval"):
            raise ValueError("缺少必要参数")
        return {
            "currency_pair": validated_data.get("code_id"),
            "from": validated_data.get("from_date"),
            "to": validated_data.get("to_date"),
            "interval": validated_data.get("interval"),
            "limit": validated_data.get("limit"),
        }

    def format(self, data, **kwargs):
        return {
            "kline": [
                {
                    "t": k[0],
                    "price": k[1],
                    "c": k[2],
                    "h": k[3],
                    "l": k[4],
                    "o": k[5],
                    "v": k[6],
                }
                for k in data
            ]
        }


_Kline = GetSetBuild()
_Kline.gate = GetKlineBuild()
