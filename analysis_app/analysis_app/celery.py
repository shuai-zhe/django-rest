import os
from celery import Celery

# 设置默认的Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'analysis_app.settings')

app = Celery('analysis_app')

# 使用字符串配置，这样worker就不需要序列化配置对象
app.config_from_object('django.conf:settings', namespace='CELERY')

# 从所有已注册的Django应用配置中加载任务模块
app.autodiscover_tasks()

