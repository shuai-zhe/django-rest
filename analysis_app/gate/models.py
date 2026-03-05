from django.db import models

# Create your models here.


class Project(models.Model):
    pid = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100,verbose_name='项目名称')
    display_name = models.CharField(max_length=100,verbose_name='项目显示名称')
    codeId = models.CharField(max_length=100,verbose_name='项目代码')
