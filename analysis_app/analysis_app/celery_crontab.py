from celery.schedules import crontab

from .celery import app

app.conf.beat_schedule = {
    "gate-spot-data": {
        "task": "get_project_data_sync",  # 使用任务名称而不是完整路径
        "schedule": crontab(minute="*/10"),
        "args": (),
    },
    "get-marsbit-market-data": {
        "task": "get_marsbit_market_data_sync",
        "schedule": crontab(minute="*/1"),
        "args": (),
    },
    "get-calendar-data": {
        "task": "get_calendar_data_sync",
        "schedule": crontab(minute="*/1"),
        "args": (),
    },
}
