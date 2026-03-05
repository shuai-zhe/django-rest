from django.shortcuts import render
from rest_framework.response import Response

# Create your views here.
from core.base import Resource
from .serializers import ProjectSerializer
from .models import Project


class ProjectResource(Resource):
    RequestSerializer = ProjectSerializer

    def list(self, request):
        """获取项目列表"""
        projects = Project.objects.all()
        # 这里可以添加序列化逻辑
        return Response({'projects': []})

    def create(self, request):
        """创建新项目"""
        validated_data = self.validate_request_data(request.data)
        # 这里处理创建逻辑
        result = self.perform_request(validated_data)
        return Response(result)

    def perform_request(self, validated_data):
        """处理业务逻辑"""
        # 这里实现具体的业务逻辑
        return {'message': 'Project created successfully', 'data': validated_data}