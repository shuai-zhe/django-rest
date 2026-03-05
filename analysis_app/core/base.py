# -*- coding: utf-8 -*-
import abc

from rest_framework import serializers
from rest_framework.serializers import Serializer
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response

# 定义一个资源类，用于自动校验views视图的入参和返回值校验
class Resource(ViewSet, metaclass=abc.ABCMeta):
    # 定义一个资源类，用于自动校验views视图的入参和返回值校验
    RequestSerializer = None
    ResponseSerializer = None
    many_request_data = False

    # 实现请求逻辑接口，不实现报错
    @abc.abstractmethod
    def perform_request(self, validated_data):
        raise NotImplementedError()

    def validate_request_data(self, request_data):
        # 校验请求参数
        if self.RequestSerializer is None:
            return request_data
        request_serializer = self.RequestSerializer(data=request_data, many=self.many_request_data)
        if not request_serializer.is_valid():
            raise serializers.ValidationError(request_serializer.errors)
        return request_serializer.validated_data

    def validate_response_data(self, response_data):
        if self.ResponseSerializer is None:
            return response_data
        response_serializer = self.ResponseSerializer(data=response_data)
        if not response_serializer.is_valid():
            raise serializers.ValidationError(response_serializer.errors)
        return response_serializer.validated_data

    def request(self, request_data):
        validate_request = self.validate_request_data(request_data)
        response_data = self.perform_request(validate_request)
        validate_response = self.validate_response_data(response_data)
        return validate_response

    # DRF ViewSet标准方法
    def list(self, request):
        # 处理GET请求（列表）
        return Response({'message': 'list method not implemented'})

    def create(self, request):
        # 处理POST请求（创建）
        return Response({'message': 'create method not implemented'})

    def retrieve(self, request, pk=None):
        # 处理GET请求（单个对象）
        return Response({'message': 'retrieve method not implemented'})

    def update(self, request, pk=None):
        # 处理PUT请求（更新）
        return Response({'message': 'update method not implemented'})

    def partial_update(self, request, pk=None):
        # 处理PATCH请求（部分更新）
        return Response({'message': 'partial_update method not implemented'})

    def destroy(self, request, pk=None):
        # 处理DELETE请求（删除）
        return Response({'message': 'destroy method not implemented'})