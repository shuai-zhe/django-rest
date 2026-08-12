import datetime
# 单独运行本文件时需先初始化 Django，否则访问 settings 会报 ImproperlyConfigured
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analysis_app.settings")
django.setup()
from django.conf import settings
from elasticsearch_dsl import Date, Keyword, Object, Text

from core.base_elasticsearch import BaseDocument


class NewDocument(BaseDocument):
    
    @classmethod
    def reset_index_(cls, doc=None):
        # 按新闻自身发布时间分区到对应月份索引；
        # doc 无 created_at 时兜底为当前月
        dt = getattr(doc, "created_at", None) if doc is not None else None
        month = (dt or datetime.datetime.now()).strftime("%Y-%m")
        return f"{settings.ES_NEWS_INDEX}_{month}"

    title = Text(
        required=True,
    )
    content = Text(
        required=True,
    )
    tag = Keyword(required=False)
    extra = Object(required=False)
    created_at = Date()

    class Index:
        name = settings.ES_NEWS_INDEX
        settings = settings.ES_CONFIG


if __name__ == "__main__":

    # 多组 mock 数据，验证 bulk_save 按 created_at 月份分区到 news_YYYY-MM
    mock_docs = [
        # 2026-01 月
        dict(title="一月新闻", content="内容A", tag="tech",
             extra={"score": 0.9}, created_at=datetime.datetime(2026, 1, 5, 10, 0, 0)),
        # 2026-03 月（跨月）
        dict(title="三月新闻", content="内容B", tag="finance",
             extra={"score": 0.8}, created_at=datetime.datetime(2026, 3, 28, 22, 0, 0)),
        # 2026-04 月
        dict(title="四月新闻", content="内容C", tag="sports",
             extra={"score": 0.7}, created_at=datetime.datetime(2026, 4, 12, 9, 0, 0)),
        # 2026-12 月（年末）
        dict(title="十二月新闻", content="内容D", tag="tech",
             extra={"score": 0.6}, created_at=datetime.datetime(2026, 12, 1, 0, 0, 0)),
        # 无 created_at：兜底为当前月（运行代码时的月份）
        dict(title="无时间新闻", content="内容E", tag="other",
             extra={"score": 0.5}),
    ]

    # 预览：bulk_save 内部会 cls(**d) 实例化，__init__ 自动按 created_at 填 meta["_index"]

    success, errors = NewDocument.bulk_save(mock_docs, chunk_size=500)
