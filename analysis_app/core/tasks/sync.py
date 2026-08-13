from celery import shared_task

from core.constants import ProjectStatus


@shared_task(name="get_project_data_sync")
def get_project_data_sync():
    from core.tasks.gate.init_update_project import ProjectMerge

    """定时更新项目数据的Celery任务"""
    project_merge = ProjectMerge(status=ProjectStatus.SPOT.value)
    project_merge.save()
    return "项目数据更新完成"


@shared_task(name="get_calendar_data_sync")
def get_calendar_data_sync():
    from core.tasks.new.init_calendar import collect_calendar

    """定时更新日历数据的Celery任务"""
    collect_calendar(resume_from_redis=True)
    return "日历数据更新完成"


@shared_task(name="get_marsbit_market_data_sync")
def get_marsbit_market_data_sync():
    from core.tasks.new.init_marsbit_market import collect_new

    """定时更新新闻市值数据的Celery任务"""
    collect_new(resume_from_redis=True)
    return "新闻市值数据更新完成"
