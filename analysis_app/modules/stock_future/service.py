from core.query_utils import QueryBuild
from modules.stock_future.models import FutureProject

from .data_build.kline_build import _StockFutureKline


class FutureService:
    def formatter(self, obj):
        # 数据暂无排名
        data = obj.values()
        return data

    def get_project_all(self, **kwargs):
        if kwargs.get("is_main"):
            query = FutureProject.active_obj.all()
        else:
            query = FutureProject.objects.all()
        # 数据过滤  防止出现异常数据
        # 至少大于0
        query = query.filter(price_dict__spot__gt=0)
        filters = kwargs.get("filters", [])
        order_by = kwargs.get("order_by", [])
        query = QueryBuild(query, filters, order_by).exec()
        return self.formatter(query)[:100]

    def get_kline_all(self, validated_data, **kwargs):
        return _StockFutureKline.stock(validated_data)
