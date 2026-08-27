from core.constants import StockTrade
from core.query_utils import QueryBuild
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
        query = StockProject.objects.all()
        filters = kwargs.get("filters", [])
        order_by = kwargs.get("order_by", [])
        query = QueryBuild(query, filters, order_by).exec()
        return self.formatter(query)[:100]

    def get_kline_all(self, validated_data, **kwargs):
        # 后续封装自动查找和错误切换
        # 多接口支持
        dtype = validated_data.get("dtype", StockTrade.BAOSTOCK.value)
        if dtype == StockTrade.BAOSTOCK.value:
            validated_data["dtype"] = dtype
            return _StockKline.stock(validated_data, **kwargs)

        raise ValueError("dtype not supported")
