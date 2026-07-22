# 基本概念
## broker消息传输【中间件：redis、kafka、rabbitMQ】
## worker 任务单元，执行的一个任务
## backend 结果端
# celery启动命令
## 启动beat定时任务
`celery -A analysis_app beat --loglevel=info`
### 使用 django_celery_beat.schedulers:DatabaseScheduler 启动 celery beat 服务：

`celery -A proj beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler`
## 启动worker[工作单元]
`celery -A analysis_app worker -P gevent --loglevel=info`
注意windows需要使用gevent进行启动否则会出现权限问题
# celery配置说明
### celery配置文件位置 `analysis_app/celery.py`
### celery参数配置位于 `analysis_app/settings.py`;(必须注册定时任务、django_celery_beat、django_celery_results)
### 定时任务定义再 `tasks/aync.py` ;(需要在[__init__.py](analysis_app/__init__.py)文件中导入确保能被django启动时加载)

# celery配置遇到的一些问题
# 根据规则必须要在app文件下配置一个 `celery.py` 文件使得Celery能够自己匹配
`[__init__.py](analysis_app/__init__.py)`
```python
from __future__ import absolute_import, unicode_literals

# 这将确保Celery应用在Django启动时被加载
from .celery import app as celery_app

# 导入定时任务配置
from . import celery_crontab

__all__ = ('celery_app',)
```
`celery.py`

```python
import os
from celery import Celery

# 设置默认的Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'analysis_app.settings')

app = Celery('analysis_app')

# 使用字符串配置，这样worker就不需要序列化配置对象
app.config_from_object('django.conf:settings', namespace='CELERY')

# 从所有已注册的Django应用配置中加载任务模块
app.autodiscover_tasks()

```

`settings.py` 
```python
INSTALLED_APPS = [
    "django_celery_beat",
    "django_celery_results",
    '...'
    'tasks',
]

# Celery Configuration
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/1'
CELERY_WORKER_CONCURRENCY = 20
CELERY_WORKER_PREFETCH_MULTIPLIER = 20
CELERY_WORKER_MAX_TASKS_PER_CHILD = 100
CELERY_TASK_ALWAYS_EAGER = False
CELERY_WORKER_DISABLE_RATE_LIMITS = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Timezone configuration
CELERY_TIMEZONE = 'Asia/Shanghai'
CELERY_ENABLE_UTC = False
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
```

# 任务的配置
`[sync.py](tasks/sync.py)`

```python
from celery import shared_task
from core.constants import ProjectStatus


@shared_task(name="get_project_data_sync")
def get_project_data_sync():
    from core.tasks import ProjectMerge
    """定时更新项目数据的Celery任务"""
    project_merge = ProjectMerge(status=ProjectStatus.SPOT.value)
    project_merge.save()
    return f"项目数据更新完成"
```
# 
`[__init__.py](tasks/__init__.py)`
```python
# tasks包初始化文件
# 使tasks目录成为有效的Python包，便于Celery自动发现任务

# 显式导入任务模块，确保Celery能够正确发现任务
from . import sync
```

# 配置定时任务执行(需要在init导入)
`[celery_crontab.py](analysis_app/celery_crontab.py)`
```python
from celery.schedules import crontab
from .celery import app
app.conf.beat_schedule = {
    'gate-spot-data': {
        'task': 'get_project_data_sync',  # 使用任务名称而不是完整路径
        'schedule': crontab(minute='*/1'),
        'args': ()
    },
}
```
