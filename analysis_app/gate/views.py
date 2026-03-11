from django.shortcuts import render
from rest_framework.response import Response

# Create your views here.
from core.base import Resource
from .serializers import ProjectSerializer
from .models import Project


class ProjectResource(Resource):
    RequestSerializer = ProjectSerializer
    method = 'POST'
    prefix = 'project'
    def perform_request(self, validated_data):
        """处理业务逻辑"""
        # 这里实现具体的业务逻辑
        return {'message': 'Project created successfully', 'data': validated_data}