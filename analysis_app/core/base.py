# -*- coding: utf-8 -*-
import abc

from django.http import HttpResponse,JsonResponse

from rest_framework import serializers, status
from rest_framework.serializers import Serializer
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from core.utils import serializer_formatter
from core.excepting import ValidateErrorException

# 定义一个资源类，用于自动校验views视图的入参和返回值校验
class Resource(APIView,metaclass=abc.ABCMeta):
    # 定义一个资源类，用于自动校验views视图的入参和返回值校验
    RequestSerializer = None
    ResponseSerializer = None
    many_request_data = False
    method = None
    prefix = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.headers = None
        self.response = None

    def dispatch(self, request, *args, **kwargs):
        # 所有请求都先到这里
        self.args = args
        self.kwargs = kwargs
        request = self.initialize_request(request, *args, **kwargs)
        self.request = request
        self.headers = self.default_response_headers  # deprecate?
        try:
            self.initial(request, *args, **kwargs)
            # 这里是找到对应的请求方法 比如 def get  def post
            # Get the appropriate handler method
            #  if request.method.lower() in self.http_method_names:
            #     handler = getattr(self, request.method.lower(),
            #                                   self.http_method_not_allowed)
            #     else:
            #         handler = self.http_method_not_allowed
            # 重写dispatch 方法，不区分请求方法,直接调用request 自定义统一流程
            response_data = self.init_request(request, *args, **kwargs)
            response = Response(response_data)

        except Exception as exc:
            response = self.handle_exception(exc)
        self.response = self.finalize_response(request, response, *args, **kwargs)
        return self.response

    @abc.abstractmethod
    def perform_request(self, validated_data):
        """
            实现请求逻辑接口，不实现报错
        """
        raise NotImplementedError()

    def validate_request_data(self, request_data):
        # 校验请求参数
        if self.RequestSerializer is None:
            return request_data
        request_serializer = self.RequestSerializer(data=request_data, many=self.many_request_data)
        if not request_serializer.is_valid():
            raise ValidateErrorException(message=serializer_formatter(request_serializer))
            # raise serializers.ValidationError(request_serializer.errors)
        return request_serializer.validated_data

    def validate_response_data(self, response_data):
        if self.ResponseSerializer is None:
            return response_data
        response_serializer = self.ResponseSerializer(data=response_data)
        if not response_serializer.is_valid():
            raise ValidateErrorException(message=serializer_formatter(response_serializer))
        return response_serializer.validated_data

    def init_request(self, request,*args, **kwargs):
        request_data = request.data if self.method=='POST' else request.query_params
        # 如果没定义method,则根据请求方法来判断；最好没有直接报错
        if not self.method:
            request_data = request.data if request.method == "POST" else request.query_params
        validate_request = self.validate_request_data(request_data)
        response_data = self.perform_request(validate_request)
        validate_response = self.validate_response_data(response_data)
        return validate_response
