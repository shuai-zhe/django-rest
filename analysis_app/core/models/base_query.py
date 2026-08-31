from django.db import models


class BaseQuery(models.QuerySet):
    def get_query(self, active=1, **kwargs):
        return super().filter(active=active)
