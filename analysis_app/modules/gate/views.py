from core.base import ResourceExtend, ResourceVail
from core.constants import KlineInterval

from .resources import ProjectKlineResource, ProjectListResource


class ProjectViewSet(ResourceExtend):
    routers = [
        ResourceVail("GET", ProjectListResource, prefix="project"),
        ResourceVail("GET", ProjectKlineResource, prefix="project/kline"),
    ]
