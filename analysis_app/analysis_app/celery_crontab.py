from celery.schedules import crontab

from .celery import app

app.conf.beat_schedule = {
    "gate-spot-data": {
        "task": "get_project_data_sync",  # 使用任务名称而不是完整路径
        "schedule": crontab(minute="*/10"),
        "args": (),
    },
}
