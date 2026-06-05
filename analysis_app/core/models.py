from django.db.models import Manager


class ProjectManager(Manager):
    def get_project(self, project_id):
        return self.get(id=project_id)