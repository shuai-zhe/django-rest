from core.base import ResourceExtend, ResourceVail

from .resources import ProjectResource


class ProjectViewSet(ResourceExtend):
    routers = [ResourceVail("GET", ProjectResource(), prefix="project")]
