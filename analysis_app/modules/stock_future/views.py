from core.base import ResourceExtend, ResourceVail

from .resources import StockFutureKlineResource, StockFutureListResource


class StockViewSet(ResourceExtend):
    routers = [
        ResourceVail(method=None, resource=StockFutureListResource, prefix="project"),
        ResourceVail("GET", StockFutureKlineResource, prefix="project/kline"),
    ]
