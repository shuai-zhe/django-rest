from core.base import ResourceExtend, ResourceVail

from .resources import ProjectKlineResource, ProjectListResource


class ProjectViewSet(ResourceExtend):
    routers = [
        ResourceVail("GET", ProjectListResource, prefix="project"),
        ResourceVail("GET", ProjectKlineResource, prefix="project/kline"),
    ]
