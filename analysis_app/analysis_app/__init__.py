from __future__ import absolute_import, unicode_literals

import pymysql

pymysql.install_as_MySQLdb()
# 导入定时任务配置
from . import celery_crontab

# 这将确保Celery应用在Django启动时被加载
from .celery import app as celery_app

__all__ = ("celery_app",)
