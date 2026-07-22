from core.base import Resource
from modules.gate.serializers import ProjectSerializer


class ProjectResource(Resource):
    RequestSerializer = ProjectSerializer

    def perform_request(self, validated_data):
        """处理业务逻辑"""
        # 这里实现具体的业务逻辑
        return validated_data
