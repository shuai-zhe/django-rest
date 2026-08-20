import datetime
import time

from apis.stock.default import BaoStockResource
from core.constants import KlineInterval
from core.utils import GetSetBuild
from modules.stock.models import StockProject

# BaoStock query_history_k_data_plus 的 frequency 与本项目 KlineInterval 的映射
# d=日线 w=周 m=月 5/15/30/60=分钟线（不区分大小写）
INTERVAL_TO_FREQ = {
    KlineInterval.D1.value: "d",
    KlineInterval.D7.value: "w",
    KlineInterval.D30.value: "m",
    KlineInterval.M5.value: "5",
    KlineInterval.M15.value: "15",
    KlineInterval.M30.value: "30",
    KlineInterval.H1.value: "60",
}


class StockKlineBuild:
    def __init__(self):
        self.params = {}

    def build_param(self, validated_data, **kwargs):
        code_id = validated_data.get("code_id")
        if not code_id or not validated_data.get("interval"):
            raise ValueError("缺少必要参数")

        # 从 DB 读取 code_type 拼成 BaoStock 需要的 code（如 sh.600000）
        project = StockProject.objects.filter(code_id=code_id).first()
        code_type = project.code_type if project else "sh"
        symbol = f"{code_type}.{code_id}"

        # 时间窗口：优先用 from_date/to_date；否则按 limit（默认 1000 根）回推
        end_date = validated_data.get("to_date") or time.strftime("%Y-%m-%d")
        limit = validated_data.get("limit") or 1000
        if validated_data.get("from_date"):
            start_date = validated_data["from_date"]
        else:
            start_date = (
                datetime.datetime.now()
                - datetime.timedelta(days=max(limit, 1) // 2 + 30)
            ).strftime("%Y-%m-%d")

        return {
            "code": symbol,
            "frequency": INTERVAL_TO_FREQ.get(validated_data["interval"], "d"),
            "start_date": start_date,
            "end_date": end_date,
        }

    def format(self, data, **kwargs):
        # BaoStockResource.stock_kline 返回的 list[dict] 经 stock_kline_format
        # 重命名后键为 t/o/h/l/c/v，其中 t 已是秒级时间戳
        klines = []
        for row in data or []:
            klines.append(
                {
                    "t": row.get("t"),
                    "o": row.get("o"),
                    "c": row.get("c"),
                    "h": row.get("h"),
                    "l": row.get("l"),
                    "v": row.get("v"),
                }
            )
        return {"kline": klines}

    def extra_format(self, data, **kwargs):
        data["interval"] = KlineInterval.values()
        return data

    def build_kline(self, validated_data, **kwargs):
        self.params = self.build_param(validated_data, **kwargs)
        raw = BaoStockResource().stock_kline(
            code=self.params["code"],
            frequency=self.params["frequency"],
            start_date=self.params["start_date"],
            end_date=self.params["end_date"],
        )
        return self.format(raw, **kwargs)

    def __call__(self, validated_data, **kwargs):
        return self.extra_format(self.build_kline(validated_data, **kwargs))


_StockKline = GetSetBuild()
_StockKline.stock = StockKlineBuild()
