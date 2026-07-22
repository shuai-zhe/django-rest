from core.base import Resource
from modules.gate.serializers import ProjectSerializer
from modules.gate.service import GateService

class ProjectListResource(Resource):
    RequestSerializer = ProjectSerializer

    def perform_request(self, validated_data):
        """处理业务逻辑"""
        # 这里实现具体的业务逻辑
        return GateService().get_project_all(**validated_data)