from core.base import Resource
from modules.stock.serializers import StockKlineSerializer, StockProjectSerializer
from modules.stock.service import StockService

logger = None  # 占位，保持与 gate resources 结构一致（如需日志自行 import）


class StockListResource(Resource):
    RequestSerializer = StockProjectSerializer

    def perform_request(self, validated_data):
        """处理业务逻辑"""
        return StockService().get_project_all(**validated_data)


class StockKlineResource(Resource):
    RequestSerializer = StockKlineSerializer

    def perform_request(self, validated_data, **kwargs):
        return StockService().get_kline_all(validated_data)
