# 定义一个路由类，用于自动注册路由
from os.path import basename

from django.urls import path
from rest_framework.routers import DefaultRouter

from core.base import Resource, ResourceExtend, ResourceVail


class ResourceRouter:
    def __init__(self, urlpatterns: list):
        self.urlpatterns = urlpatterns

    def register_module(self, viewset_module, prefix=None):
        # 注册views视图的所有 Resource类，根据命名规则自动注册路由
        for name, viewset in viewset_module.__dict__.items():
            # 全部小写不是类,并且类不等于 名字不等于Resource
            if name.lower() == name or name == "Resource":
                continue
            # 确保viewset是一个类
            if not isinstance(viewset, type):
                continue

            for resource_view in getattr(viewset, "routers", []):
                if not isinstance(getattr(resource_view, "resource", None), Resource):
                    continue
                self.urlpatterns.append(
                    path(
                        resource_view.prefix or name.lower(),
                        resource_view.resource.as_view(),
                    )
                )
