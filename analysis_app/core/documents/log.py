import datetime

from django.conf import settings
from elasticsearch_dsl import Date, Keyword, Text

from core.base_elasticsearch import BaseDocument


class LogDocument(BaseDocument):
    """应用日志文档，按 timestamp 月份分区写入 app-logs_YYYY-MM。"""

    @classmethod
    def reset_index_(cls, doc=None):
        ts = getattr(doc, "timestamp", None) if doc is not None else None
        month = (ts or datetime.datetime.now()).strftime("%Y-%m")
        return f"app-logs_{month}"

    timestamp = Date()
    level = Keyword()
    logger_name = Keyword()
    service = Keyword()
    env = Keyword()
    module = Keyword()
    message = Text(analyzer="ik_smart", search_analyzer="ik_smart")
    exc_info = Text()

    class Index:
        name = "app-logs"
        # ES_CONFIG 已在 dev.py 中合并 IK 的 analysis 配置
        settings = settings.ES_CONFIG
