# 定义一个路由类，用于自动注册路由
from os.path import basename

from django.urls import path
from rest_framework.routers import DefaultRouter

from core.base import Resource


class ResourceRouter():
    def __init__(self, urlpatterns:list):
        self.urlpatterns = urlpatterns
    def register_module(self, viewset_module, prefix=None):
        # 注册views视图的所有 Resource类，根据命名规则自动注册路由
        for name, viewset in viewset_module.__dict__.items():
            # 全部小写不是类,并且类不等于 名字不等于Resource
            if name.lower()==name or  name == "Resource" :
                continue
            # 确保viewset是一个类
            if not isinstance(viewset, type):
                continue
            # 继承了Resource类开始注册
            if issubclass(viewset, Resource):
                self.urlpatterns.append(path(viewset.prefix or name.lower(), viewset.as_view()))

