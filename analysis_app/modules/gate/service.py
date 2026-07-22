from modules.gate.models import Project


class GateService:
    def formatter(self, obj):
        return obj.values()

    def get_project_all(self, **kwargs):
        return self.formatter(Project.objects.all())
