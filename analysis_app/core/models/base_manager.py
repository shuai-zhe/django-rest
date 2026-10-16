from django.db import models

from .base_query import BaseQuery


class BaseManager(models.Manager):
    def get_queryset(self):
        return BaseQuery(self.model).get_query()
