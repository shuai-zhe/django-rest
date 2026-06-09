from celery import shared_task
from core.constants import ProjectStatus


@shared_task(name="get_project_data_sync")
def get_project_data_sync():
    from tasks.gate.init_update_project import ProjectMerge
    """定时更新项目数据的Celery任务"""
    project_merge = ProjectMerge(status=ProjectStatus.SPOT.value)
    project_merge.save()
    return f"项目数据更新完成"