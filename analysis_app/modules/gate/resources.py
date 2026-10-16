import logging

from core.base import Resource
from core.utils import sync_project_analysis
from modules.gate.models import Project
from modules.gate.serializers import ProjectKlineSerializer, ProjectSerializer
from modules.gate.service import GateService

logger = logging.getLogger(__name__)


class ProjectListResource(Resource):
    RequestSerializer = ProjectSerializer

    def perform_request(self, validated_data):
        """处理业务逻辑"""
        # 这里实现具体的业务逻辑
        return GateService().get_project_all(**validated_data)


class ProjectKlineResource(Resource):
    RequestSerializer = ProjectKlineSerializer

    def perform_request(self, validated_data, **kwargs):
        data = GateService().get_kline_all(validated_data)
        # 每次请求 K 线时，复用本次已返回的 K 线数据更新一次 Project 表的 24h 统计
        code_id = validated_data.get("code_id")
        if code_id:
            sync_project_analysis(data, code_id, Project)
        return data
