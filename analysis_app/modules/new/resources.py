from core.base import Resource

from .serializers import NewDetailSerializer, NewSearchSerializer
from .service import NewService


class NewListResource(Resource):
    RequestSerializer = NewSearchSerializer

    def perform_request(self, validated_data):
        """处理新闻列表查询业务逻辑"""
        return NewService().get_new_list(**validated_data)


class NewDetailResource(Resource):
    RequestSerializer = NewDetailSerializer

    def perform_request(self, validated_data):
        """处理新闻详情查询业务逻辑"""
        return NewService().get_new_detail(**validated_data)
