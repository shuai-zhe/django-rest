from apis.stock.default import AkShareStockResource
from core.constants import KlineInterval
from core.utils import GetSetBuild

# BaoStock query_history_k_data_plus 的 frequency 与本项目 KlineInterval 的映射
# d=日线 w=周 m=月 5/15/30/60=分钟线（不区分大小写）
INTERVAL_TO_FREQ = {
    KlineInterval.M5.value: "5",
    KlineInterval.M15.value: "15",
    KlineInterval.M30.value: "30",
    KlineInterval.H1.value: "60",
    KlineInterval.D1.value: "d",
    # KlineInterval.D7.value: "w",
    # KlineInterval.D30.value: "m",
}


class StockFutureKlineBuild:
    def __init__(self):
        self.params = {}

    def build_param(self, validated_data, **kwargs):
        code_id = validated_data.get("code_id")
        if not code_id or not validated_data.get("interval"):
            raise ValueError("缺少必要参数")
        # 暂时不切换查询点
        # 从 DB 读取 code_type 拼成 BaoStock 需要的 code（如 sh.600000）
        # project = FutureProject.objects.filter(code_id=code_id).first()
        # if interval in ["daily", "weekly", "monthly"]:
        # symbol = project.get_stock_id(validated_data.get("dtype"))
        return {"interval": validated_data.get("interval", ""), "code_id": code_id}

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
        data["interval"] = list(INTERVAL_TO_FREQ.keys())
        return data

    def build_kline(self, validated_data, **kwargs):
        self.params = self.build_param(validated_data, **kwargs)
        raw = AkShareStockResource().future_kline(**self.params)
        return self.format(raw, **kwargs)

    def __call__(self, validated_data, **kwargs):
        return self.extra_format(self.build_kline(validated_data, **kwargs))


_StockFutureKline = GetSetBuild()
_StockFutureKline.stock = StockFutureKlineBuild()


if __name__ == "__main__":
    data = {
        "code_id": "PxXx61x1".upper(),
        "interval": "15m",
        "start_date": "2026-08-01",
        "end_date": "2026-08-21",
    }
    print(_StockFutureKline.stock(data))
