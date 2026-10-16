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
        "schedule": crontab(minute="*/10"),
        "args": (),
    },
    "get-calendar-data": {
        "task": "get_calendar_data_sync",
        "schedule": crontab(minute="*/240"),
        "args": (),
    },
    "get-stock-data": {
        "task": "get_stock_data_sync",
        # 每 10 分钟检查一次；任务内部仅在「周一至周五 且 15:00 收盘之后」才真正同步
        "schedule": crontab(minute="*/30"),
        "args": (),
    },
    "get-stock-future-data": {
        "task": "get_stock_future_data_sync",
        # 每 10 分钟检查一次；任务内部仅在「周一至周五 且 15:00 收盘之后」才真正同步
        "schedule": crontab(minute="*/30"),
        "args": (),
    },
}
