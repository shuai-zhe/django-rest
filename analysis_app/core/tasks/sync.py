import datetime

from celery import shared_task

from core.constants import ProjectStatus


def is_a_share_trading_open() -> bool:
    """判断当前是否处于 A 股（中国内地）的交易时段，允许同步。

    A 股交易时间：周一至周五，上午 09:30-11:30，下午 13:00-15:00
    （中午 11:30 收盘，13:00 重新开盘，下午 15:00 最终收盘）。
    仅当「工作日 且 处于开盘交易区间内」才允许同步；午休、收盘后、周末均停止。
    """
    now = datetime.datetime.now()
    # 周一=0 ... 周日=6，周末（5、6）直接跳过
    if now.weekday() >= 5:
        return False
    # 交易时段一：上午 09:30-11:30
    if (
        (now.hour == 9 and now.minute >= 30)
        or (now.hour == 10)
        or (now.hour == 11 and now.minute < 30)
    ):
        return True
    # 交易时段二：下午 13:00-16:00（不含 16:00 整点收盘后）
    if (
        (now.hour == 13)
        or (now.hour == 14)
        or (now.hour == 16 and now.minute == 0 and now.second == 0)
    ):
        return True
    # 午休 11:30-13:00、收盘后 15:00 之后：停止同步
    return False


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


@shared_task(name="get_stock_data_sync")
def get_stock_data_sync():
    from core.tasks.stock.init_stock_project import StockMerge

    # A 股仅在周一至周五的交易时段（09:30-11:30、13:00-15:00）内同步，午休/收盘后/周末停止
    if not is_a_share_trading_open():
        return "非 A 股交易时段，跳过股票数据更新"

    stock_merge = StockMerge(status=ProjectStatus.SPOT.value)
    stock_merge.save()
    return "股票数据更新完成"
