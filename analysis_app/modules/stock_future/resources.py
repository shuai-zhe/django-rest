import logging

from core.base import Resource
from core.utils import sync_project_analysis
from modules.stock_future.models import FutureProject
from modules.stock_future.serializers import (
    StockFutureKlineSerializer,
    StockFutureProjectSerializer,
)
from modules.stock_future.service import FutureService

logger = logging.getLogger(__name__)


class StockFutureListResource(Resource):
    RequestSerializer = StockFutureProjectSerializer

    def perform_request(self, validated_data):
        """处理业务逻辑"""
        return FutureService().get_project_all(**validated_data)


class StockFutureKlineResource(Resource):
    RequestSerializer = StockFutureKlineSerializer

    def perform_request(self, validated_data, **kwargs):
        data = FutureService().get_kline_all(validated_data)
        code_id = validated_data.get("code_id")
        if code_id:
            sync_project_analysis(data, code_id, FutureProject)
        return data
