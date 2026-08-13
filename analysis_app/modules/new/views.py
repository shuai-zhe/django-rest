from core.base import ResourceExtend, ResourceVail

from .resources import NewListResource


class NewViewSet(ResourceExtend):
    routers = [
        ResourceVail("GET", NewListResource, prefix="list"),
    ]
