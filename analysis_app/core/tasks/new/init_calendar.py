"""
新闻日历数据采集：按时间范围分页拉取 panews 日历事件，批量写入 ES 月份分区索引。

单独运行： python core/tasks/gate/init_calendar.py
"""
import datetime
import logging
import time

from django.core.cache import cache

from apis.new.default import _NewApi
from core.documents.new import NewDocument

logger = logging.getLogger("init_new")

# 接口单页最大条数（take 上限 100）
PAGE_SIZE = 100
# 接口时间参数为 UTC 格式
UTC_FORMAT = "%Y-%m-%dT%H:%M:%S.000Z"
# 本地时区偏移（Asia/Shanghai）
UTC_OFFSET = datetime.timedelta(hours=8)
# Redis 键：记录日历采集的状态点（当前年月日，格式 YYYY-MM-DD）
CALENDAR_SYNC_DATE_KEY = "panews:calendar:last_sync_date"


def set_calendar_sync_date(sync_date: datetime.date = None):
    """
    将日历采集的状态点写入 Redis。默认记录当前年月日。
    这里不根据数据采集情况动态设置，仅作为"本次采集运行日"的标记。
    """
    sync_date = sync_date or datetime.date.today()
    date_str = sync_date.strftime("%Y-%m-%d")
    cache.set(CALENDAR_SYNC_DATE_KEY, date_str, timeout=None)  # 永久保存，直到下次覆盖
    logger.info(f"更新日历状态点 -> Redis[{CALENDAR_SYNC_DATE_KEY}] = {date_str}")


def get_calendar_sync_date():
    """读取 Redis 中记录的日历状态点（YYYY-MM-DD 字符串），无记录返回 None"""
    val = cache.get(CALENDAR_SYNC_DATE_KEY)
    return val if val else None


def to_utc_str(dt: datetime.datetime) -> str:
    """本地时间(UTC+8) 转换为接口需要的 UTC 字符串"""
    return (dt - UTC_OFFSET).strftime(UTC_FORMAT)


def build_start_at(start_time: datetime.datetime, end_time: datetime.datetime) -> str:
    """构造 startAt 区间过滤参数：between,起始UTC,结束UTC"""
    return f"between,{to_utc_str(start_time)},{to_utc_str(end_time)}"


def collect_calendar(
    start_time=None,
    end_time=None,
    page_size=PAGE_SIZE,
    sleep=0.5,
    resume_from_redis=False,
):
    """
    分页采集指定时间范围内的日历数据并写入 ES
    :param start_time: 采集起始时间（本地时间）
    :param end_time: 采集结束时间（本地时间），默认当前时间
    :param page_size: 每页条数，接口上限 100
    :param sleep: 每页请求间隔，避免触发风控
    :param resume_from_redis: 是否从检查点（Redis 记录的 last_sync_date）开始采集。
                              为 True 时，用 Redis 中的状态点日期作为 start_time，
                              只采集该日期之后的数据（增量模式）。
    :return: (成功条数, 失败条数)
    """
    # 从检查点开始：用 Redis 里记录的年月日作为采集起始时间
    if resume_from_redis:
        date_str = get_calendar_sync_date()
        if date_str is not None:
            y, m, d = (int(_) for _ in date_str.split("-"))
            start_time = datetime.datetime(y, m, d, 0, 0, 0)
            logger.info(f"从检查点续传：Redis 状态点={date_str} -> start_time={start_time}")
        else:
            # Redis 无状态点记录：回退到默认起始时间，避免 start_time 为 None 导致崩溃
            start_time = datetime.datetime(2026, 1, 1)
            logger.warning(
                "resume_from_redis=True 但 Redis 无状态点记录，回退默认起始时间 start_time=2026-01-01"
            )

    end_time = end_time or datetime.datetime.now()
    start_at = build_start_at(start_time, end_time)
    logger.info(f"开始采集：{start_time} ~ {end_time}，startAt={start_at}")

    skip = 0
    total_success, total_failed = 0, 0
    while True:
        data = _NewApi.calendar({"take": page_size, "skip": skip, "startAt": start_at})
        if not data:
            break
        # 数据源返回的 _id 会作为文档 _id 写入，重复采集时为覆盖更新，天然幂等
        success, errors = NewDocument.bulk_save(data, chunk_size=page_size)
        total_success += success
        total_failed += len(errors)
        logger.info(f"skip={skip} 拉取 {len(data)} 条，写入成功 {success} 条，失败 {len(errors)} 条")
        if errors:
            logger.error(f"skip={skip} 写入失败明细：{errors[:3]}")
        # 返回条数不足一页说明已到最后一页
        if len(data) < page_size:
            break
        skip += page_size
        time.sleep(sleep)

    logger.info(f"采集完成：成功 {total_success} 条，失败 {total_failed} 条")
    # 采集完成，把当前年月日作为状态点写入 Redis（不依赖具体采集数据）
    set_calendar_sync_date()
    return total_success, total_failed


if __name__ == "__main__":
    import os

    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analysis_app.settings")
    django.setup()
    # 仅在没有任何 handler 时兜底（脱离 Django 单独运行场景），
    # 避免与 settings.py 中的统一 LOGGING 配置重复输出
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )
    # 采集 2026-06-01 至今的数据
    # collect_calendar(start_time=datetime.datetime(2026, 1, 1))
    collect_calendar(resume_from_redis=True)
