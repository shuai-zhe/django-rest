from django.db.models import F, Func, Value

from core.constants import StockTrade
from modules.stock.models import StockProject

from .data_build.kline_build import _StockKline


class StockService:
    def formatter(self, obj):
        # 数据暂无排名

        data = obj.values()
        for index, value in enumerate(data):
            value["extra_info"]["rank"] = index + 1
        return data

    def get_project_all(self, **kwargs):
        _ = StockProject.active_obj.filter()
        filter_format = kwargs.get("filter_format", {})
        if filter_format:
            _ = _.filter(**filter_format)
        # 股票类型在后台限制最多展示 500 条数据
        # 按 extra_info.performance.day 的绝对值降序（正负一视同仁）
        day_abs = Func(
            Func(
                F("extra_info"),
                Value("$.performance.day"),
                function="JSON_EXTRACT",
            ),
            function="ABS",
        )
        _ = _.order_by(day_abs.desc())[:500]
        return self.formatter(_)

    def get_kline_all(self, validated_data, **kwargs):
        # 后续封装自动查找和错误切换
        # 多接口支持
        dtype = validated_data.get("dtype", StockTrade.BAOSTOCK.value)
        if dtype == StockTrade.BAOSTOCK.value:
            validated_data["dtype"] = dtype
            return _StockKline.stock(validated_data, **kwargs)

        raise ValueError("dtype not supported")
