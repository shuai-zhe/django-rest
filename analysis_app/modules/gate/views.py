from core.base import ResourceExtend, ResourceVail

from .resources import ProjectKlineResource, ProjectListResource


class ProjectViewSet(ResourceExtend):
    routers = [
        ResourceVail(method=None, resource=ProjectListResource, prefix="project"),
        ResourceVail(
            method="GET", resource=ProjectKlineResource, prefix="project/kline"
        ),
    ]
