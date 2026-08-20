from core.base import ResourceExtend, ResourceVail

from .resources import StockKlineResource, StockListResource


class StockViewSet(ResourceExtend):
    routers = [
        ResourceVail("GET", StockListResource, prefix="project"),
        ResourceVail("GET", StockKlineResource, prefix="project/kline"),
    ]
