"""
新闻数据采集（marsbit）：按 currentPage 分页拉取 /info/lives/showlives 快讯，
逐页写入 ES 月份分区索引。返回体为分页结构：
    {
      "code": 1, "msg": "ok",
      "obj": {"pageSize": 100, "recordCount": 1000, "currentPage": 1,
              "pageCount": 10, "currentTime": ..., "inforList": [...]}
    }
接口越往后翻页时间越早，翻到最后一页（数据不足一页）即可停止。

单独运行： python core/tasks/new/init_marsbit_market.py
"""
import datetime
import logging
import time

from django.core.cache import cache

from apis.new.default import _NewApi
from core.documents.new import NewDocument

logger = logging.getLogger("init_new")

# 单次请求最大每页条数（接口上限 100）
PAGE_SIZE = 100
# 频道：21 对应快讯频道；如需调整可改这里
CHANNEL_ID = 21
# 每页请求间隔，避免触发风控
SLEEP = 0.5
# 截止日期：采集到 created_at <= 该时间时停止（接口越往后时间越早）
STOP_DATE = datetime.datetime(2026, 1, 1, 0, 0, 0)
# Redis 键：记录最近一次采集到的最新位置（第一页第一条 createdTime 的时间戳，毫秒）
LATEST_POSITION_KEY = "marsbit:market:latest_position"


def get_latest_position():
    """读取 Redis 中记录的最新位置时间戳（毫秒级），无记录返回 None"""
    val = cache.get(LATEST_POSITION_KEY)
    return int(val) if val is not None else None


def set_latest_position(created_at: datetime.datetime):
    """
    将本次采集第一页第一条的 created_at 写入 Redis，作为最新位置。
    存为毫秒级时间戳，便于与接口 createdTime 直接比较。
    """
    if created_at is None:
        return
    ts_ms = int(created_at.timestamp() * 1000)
    cache.set(LATEST_POSITION_KEY, ts_ms, timeout=None)  # 永久保存，直到下次覆盖
    logger.info(f"更新最新位置 -> Redis[{LATEST_POSITION_KEY}] = {ts_ms} ({created_at})")


def collect_new(
    channel_id=CHANNEL_ID,
    page_size=PAGE_SIZE,
    sleep=SLEEP,
    stop_date=STOP_DATE,
    resume_from_redis=False,
):
    """
    无限分页采集 marsbit 快讯并写入 ES，直到数据时间 <= stop_date 为止。

    接口越往后翻页时间越早，因此逐页向后翻，一旦某条数据 created_at 早于
    （或等于）stop_date，其后的数据都更早，无需再抓，截取后停止。

    每次启动：将第一页第一条（最新）数据的 created_at 写入 Redis，作为最新位置记录。

    :param channel_id: 频道 ID
    :param page_size: 每页条数（接口上限 100）
    :param sleep: 每页请求间隔（秒）
    :param stop_date: 截止日期，数据时间 <= 该值时停止采集
    :param resume_from_redis: 是否从中断点（Redis 记录的最新位置）开始采集。
                              为 True 时，用 Redis 中的 latest_position 替换 stop_date，
                              只采集比上次最新位置更新的数据（增量模式）。
    :return: (成功条数, 失败条数)
    """
    # 从中断点开始：用 Redis 里记录的最新位置（毫秒时间戳）作为截止日期
    if resume_from_redis:
        latest_ts = get_latest_position()
        if latest_ts is not None:
            stop_date = datetime.datetime.fromtimestamp(latest_ts / 1000)
            logger.info(f"从中断点续传：Redis 最新位置={latest_ts} -> stop_date={stop_date}")
        else:
            logger.warning("resume_from_redis=True 但 Redis 无最新位置记录，回退为默认 stop_date")

    total_success, total_failed = 0, 0
    current_page = 1
    recorded_latest = False

    while True:
        query = (
            f"?currentPage={current_page}"
            f"&pageSize={page_size}"
            f"&channelId={channel_id}"
            f"&passportid=&lang=zh-CN"
        )
        # _NewApi.new 内部 NEW_FORMATTER 已解析 obj.inforList 并提取字段
        data = _NewApi.new(query)
        if not data:
            logger.info(f"currentPage={current_page} 返回空，停止采集")
            break

        # 第一页第一条即接口最新数据：记录为本次采集的最新位置
        if not recorded_latest and data:
            set_latest_position(data[0].get("created_at"))
            recorded_latest = True
            logger.info(f"本次采集最新位置（第一页第一条）：{data[0].get('created_at')}")

        # 接口越往后时间越早，同一页内时间递减：遇到第一条 <= stop_date 的数据，
        # 其后的都不需要，截断后停止采集
        if stop_date is not None:
            cut = len(data)
            for idx, item in enumerate(data):
                created_at = item.get("created_at")
                if created_at is not None and created_at <= stop_date:
                    cut = idx  # 截止日期当天的数据仍采集（<= 包含等号）
                    break
            data = data[:cut]
        if not data:
            logger.info(f"过滤后:currentPage={current_page} 返回空，停止采集")
            break
        if data:
            success, errors = NewDocument.bulk_save(data, chunk_size=page_size)
            total_success += success
            total_failed += len(errors)
            logger.info(
                f"currentPage={current_page} 拉取 {len(data)} 条，"
                f"写入成功 {success} 条，失败 {len(errors)} 条"
            )
            if errors:
                logger.error(f"currentPage={current_page} 写入失败明细：{errors[:3]}")
        else:
            logger.info(f"currentPage={current_page} 数据均在截止日期之前，跳过写入")

        current_page += 1
        time.sleep(sleep)

    logger.info(f"采集完成：成功 {total_success} 条，失败 {total_failed} 条")
    return total_success, total_failed


if __name__ == "__main__":
    import os

    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analysis_app.settings")
    django.setup()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    # 全量采集（从最新一页往后翻，直到最早一页）
    collect_new(resume_from_redis=True)
