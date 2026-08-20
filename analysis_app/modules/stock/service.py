from modules.stock.models import StockProject

from .data_build.kline_build import _StockKline


class StockService:
    def formatter(self, obj):
        return obj.values()

    def get_project_all(self, **kwargs):
        _ = StockProject.objects.filter()
        filter_format = kwargs.get("filter_format", {})
        if filter_format:
            _ = _.filter(**filter_format)
        # 股票类型在后台限制最多展示 500 条数据
        _ = _.order_by("-market_cap_dict__SPOT")[:500]
        return self.formatter(_)

    def get_kline_all(self, validated_data, **kwargs):
        # 后续封装自动查找和错误切换
        return _StockKline(validated_data, **kwargs)
