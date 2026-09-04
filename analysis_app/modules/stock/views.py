from core.base import ResourceExtend, ResourceVail

from .resources import StockKlineResource, StockListResource


class StockViewSet(ResourceExtend):
    routers = [
        ResourceVail(method=None, resource=StockListResource, prefix="project"),
        ResourceVail("GET", StockKlineResource, prefix="project/kline"),
    ]
