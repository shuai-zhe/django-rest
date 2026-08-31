# 基础的模型配置
from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    create_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    active = models.IntegerField(default=1, verbose_name="是否有效")

    def base_save(self):
        if not self.pk:
            # 新建
            self.create_time = timezone.now()
        self.update_at = timezone.now()

    def save(self, *args, **kwargs):
        # 更新基础方法
        self.base_save()
        super().save(*args, **kwargs)

    class Meta:
        abstract = True
