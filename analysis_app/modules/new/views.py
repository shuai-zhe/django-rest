from core.base import ResourceExtend, ResourceVail

from .resources import NewDetailResource, NewListResource


class NewViewSet(ResourceExtend):
    routers = [
        ResourceVail("GET", NewListResource, prefix="list"),
        ResourceVail("GET", NewDetailResource, prefix="detail"),
    ]
