"""
新闻模块 URL 配置：使用 ResourceRouter 自动注册 Resource 路由。
"""

from core.routes import ResourceRouter

from . import views

app_name = "stock"
urlpatterns = []

ResourceRouter(urlpatterns).register_module(viewset_module=views)
