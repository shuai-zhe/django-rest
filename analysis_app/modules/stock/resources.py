import logging

from core.base import Resource
from core.utils import sync_project_analysis
from modules.stock.models import StockProject
from modules.stock.serializers import StockKlineSerializer, StockProjectSerializer
from modules.stock.service import StockService

logger = logging.getLogger(__name__)


class StockListResource(Resource):
    RequestSerializer = StockProjectSerializer

    def perform_request(self, validated_data):
        """处理业务逻辑"""
        return StockService().get_project_all(**validated_data)


class StockKlineResource(Resource):
    RequestSerializer = StockKlineSerializer

    def perform_request(self, validated_data, **kwargs):
        data = StockService().get_kline_all(validated_data)
        code_id = validated_data.get("code_id")
        if code_id:
            sync_project_analysis(data, code_id, StockProject)
        return data
