from core.base import ResourceExtend, ResourceVail

from .resources import ProjectListResource


class ProjectViewSet(ResourceExtend):
    routers = [
        ResourceVail("GET", ProjectListResource(), prefix="project")
    ]
