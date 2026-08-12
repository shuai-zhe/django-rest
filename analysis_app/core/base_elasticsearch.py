import time

import pandas as pd
from django.conf import settings
from elasticsearch_dsl import Document, connections
from elasticsearch.helpers import bulk

# 方向A：不引入 django_elasticsearch_dsl，仅用 elasticsearch_dsl 的 connections 注册 default 连接。
# 放在模块导入阶段，确保任何 Document（save/bulk/search）使用前连接已就绪，
# 覆盖 Django 启动、Celery worker 等场景（无需将 django_elasticsearch_dsl 加入 INSTALLED_APPS）。
_client_cfg = {
    "hosts": settings.ES_HOSTS,
    "timeout": settings.ES_TIMEOUT,
}
if getattr(settings, "ES_USERNAME", "") and getattr(settings, "ES_PASSWORD", ""):
    _client_cfg["basic_auth"] = (settings.ES_USERNAME, settings.ES_PASSWORD)
connections.configure(default=_client_cfg)


class BaseDocument(Document):
    # 扩展 实现共有方法

    @classmethod
    def reset_index_(cls, doc=None):
        # 解析当前数据的索引
        return cls._index

    def get_index(self):
        # HitMeta 没有 .get() 方法，用下标访问并兜底到默认索引名
        try:
            return self.meta["_index"]
        except (KeyError, AttributeError):
            return self._index._name

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "_index" not in self.meta:
            self.meta["_index"] = self.reset_index_(self)

    def build_date_index(
        self, start_time=None, end_time=None, freq=None, strftime=None
    ):
        # 构造查询索引，默认返回查询所有，
        # start_time + day 查询开始至当前时间内的所有day索引
        # end_time + day 查询数据库开始时间至结束时间
        # 如果存在date 必须先校验
        # 提前构造时间范围
        start_time = start_time or settings.ES_NEWS_START_TIME
        end_time = end_time or time.strftime(self.DATE_FORMAT)
        return list(
            pd.date_range(start_time, end_time, freq=freq).strftime(strftime).tolist()
        )

    def build_all_index(self, use_index_list: list = None):
        if use_index_list:
            return [f"{_index}_*" for _index in use_index_list]
        return f"{self._index}_*"

    def search(
        self,
        using=None,
        index=None,
        all_index=None,
        start_time=None,
        end_time=None,
        freq=None,
        strftime=None,
    ):
        """
        搜索数据；如果index存在 直接调用查询；如果all_index存在 直接调用查询所有索引
        """
        if index:
            return super().search(using=using, index=index)

        if all_index:
            return super().search(using=using, index=self.build_all_index())

        # 如果index和all_index都不存在，使用时间范围查询
        date_index = self.build_all_index(
            self.build_date_index(
                start_time=start_time, end_time=end_time, freq=freq, strftime=strftime
            )
        )
        return super().search(using=using, index=date_index)

    @classmethod
    def bulk_save(cls, docs, chunk_size=500):
        # bulk是一个能够批量创建的函数，能够对dict或者document进行批量创建；
        # 这里主要是对数据进行分区格式创建
        actions = []
        for d in docs:
            if isinstance(d, dict):
                doc = cls(**d)
            else:
                doc = d
            # 优先使用实例化时已自动填充的月份索引；
            # 若 meta 未带 _index，则按 doc 内容兜底计算（如直接传 Document 实例时）
            if "_index" not in doc.meta:
                doc.meta["_index"] = cls.reset_index_(doc)
            doc_todict = doc.to_dict(include_meta=True)
            # to_dict(include_meta=True) 导出的 _index 取自 class Index.name（固定 "news"），
            # 必须手动覆盖为分区后的月份索引，否则全部写入单一索引 news
            doc_todict["_index"] = doc.meta["_index"]
            actions.append(doc_todict)
        return bulk(
            cls._get_connection(),
            actions,
            chunk_size=chunk_size,
            raise_on_error=False,  # 单条失败不中断，错误进 errors
            raise_on_exception=False,
        )
