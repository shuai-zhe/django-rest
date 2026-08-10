"""Elasticsearch 客户端封装（基于 elasticsearch-dsl）。

用于新闻数据的存储与检索。连接参数取自 Django settings 中
analysis_app.config 注入的 ES_* 配置项。

使用方式：
    from core.tools.elasticsearch_client import es_client, NewsDocument, NewsESStore

    # 初始化索引（首次部署或变更 mapping 时调用）
    es_client.ensure_index()

    # 用 NewsDocument 定义并写入一条新闻（默认以 url 作为幂等主键）
    news = NewsDocument(
        title="xxx", content="xxx", source="xxx",
        url="https://news.example.com/123",
        publish_time="2026-08-10T10:00:00",
    )
    news.save()

    # 也可通过存储层批量写入
    NewsESStore.bulk_save([news])

    # 关键词检索
    hits = NewsESStore.search("人工智能", size=10)
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from django.conf import settings
from elasticsearch_dsl import (
    Date,
    Document,
    Index,
    Keyword,
    Object,
    Text,
    analyzer,
    connections,
)

# 中文分词分析器：使用 ik_max_word（需安装 ik 插件）；
# 若未安装 ik 插件，可改为 analyzer("news_analyzer", "standard") 或 "simple"。
news_analyzer = analyzer(
    "news_analyzer",
    tokenizer="ik_max_word",
)


class NewsDocument(Document):
    """新闻文档模型（继承 elasticsearch_dsl.Document）。

    字段定义、类型、analyzer 全部集中在此类，mapping 自动生成，
    无需再维护一份独立的 NEWS_INDEX_SETTINGS。
    """

    title = Text(analyzer=news_analyzer, fields={"keyword": Keyword(ignore_above=256)})
    content = Text(analyzer=news_analyzer)
    summary = Text(analyzer=news_analyzer)

    source = Keyword()
    author = Keyword()
    url = Keyword()
    category = Keyword()
    tags = Keyword()

    publish_time = Date()
    crawl_time = Date()
    extra = Object(enabled=False)

    class Index:
        # 索引名默认 news，可在 Django 启动后由 es_client 动态覆盖
        name = getattr(settings, "ES_NEWS_INDEX", "news")
        # 索引级 settings
        settings = {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        }


class ElasticsearchClient:
    """ES 连接管理（基于 elasticsearch-dsl connections）。

    单例，按需建立连接；同时负责把 NewsDocument 的索引名
    对齐到 Django settings 中的 ES_NEWS_INDEX。
    """

    _instance: Optional["ElasticsearchClient"] = None
    _client = None

    def __new__(cls) -> "ElasticsearchClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def client(self):
        if self._client is None:
            self._client = self._build_connection()
        return self._client

    def _build_connection(self):
        hosts = getattr(settings, "ES_HOSTS", "http://127.0.0.1:8072")
        username = getattr(settings, "ES_USERNAME", "")
        password = getattr(settings, "ES_PASSWORD", "")
        timeout = getattr(settings, "ES_TIMEOUT", 30)

        host_list = [h.strip() for h in hosts.split(",") if h.strip()]
        kwargs: Dict[str, Any] = {
            "hosts": host_list,
            "request_timeout": timeout,
        }
        if username:
            kwargs["http_auth"] = (username, password)

        conn = connections.create_connection(alias="default", **kwargs)

        # 让 NewsDocument 的索引名与 settings 保持一致
        index_name = getattr(settings, "ES_NEWS_INDEX", "news")
        if NewsDocument._index._name != index_name:
            NewsDocument._index = Index(index_name)
            NewsDocument._index.settings(**NewsDocument.Index.settings)

        return conn

    @property
    def index_name(self) -> str:
        return NewsDocument._index._name

    def ping(self) -> bool:
        """检查 ES 是否可达。"""
        try:
            return bool(self.client.ping())
        except Exception:
            return False

    def ensure_index(self, recreate: bool = False) -> None:
        """确保新闻索引存在（不存在则创建）。recreate=True 会先删后建。"""
        if recreate:
            NewsDocument._index.delete(ignore=404)
        if not NewsDocument._index.exists():
            NewsDocument.init()

    def index_exists(self) -> bool:
        return bool(NewsDocument._index.exists())


class NewsESStore:
    """新闻数据读写操作（基于 NewsDocument）。"""

    def __init__(self, client: Optional[ElasticsearchClient] = None) -> None:
        self._es = client or ElasticsearchClient()

    def save(self, doc: NewsDocument, doc_id: Optional[str] = None) -> str:
        """保存一条新闻文档，返回其 id（默认 url）。"""
        if doc_id is not None:
            doc.meta.id = doc_id
        elif doc.url:
            doc.meta.id = doc.url
        doc.save(using="default", index=NewsDocument._index._name)
        return doc.meta.id

    def bulk_save(self, docs: Iterable[NewsDocument], id_key: str = "url") -> List[str]:
        """批量保存新闻文档（按 id_key 去重幂等）。返回写入的 id 列表。"""
        ids: List[str] = []
        for doc in docs:
            _id = getattr(doc, id_key, None)
            if _id is not None:
                doc.meta.id = _id
            doc.save(using="default", index=NewsDocument._index._name)
            ids.append(doc.meta.id)
        return ids

    def get(self, doc_id: str) -> Optional[NewsDocument]:
        try:
            return NewsDocument.get(id=doc_id, using="default")
        except Exception:
            return None

    def delete(self, doc_id: str) -> bool:
        try:
            doc = NewsDocument.get(id=doc_id, using="default")
            doc.delete(using="default")
            return True
        except Exception:
            return False

    def search(
        self,
        keyword: str = "",
        fields: Optional[List[str]] = None,
        size: int = 10,
        from_: int = 0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """按关键词检索新闻，支持多字段匹配与过滤。

        filters 示例：{"source": "新华网", "category": "科技"}
        """
        fields = fields or ["title", "content", "summary"]

        s = NewsDocument.search(using="default")
        if keyword:
            s = s.query("multi_match", query=keyword, fields=fields, type="best_fields")
        else:
            s = s.query("match_all")

        if filters:
            for k, v in filters.items():
                if v is not None:
                    s = s.filter("term", **{k: v})

        s = s.sort({"publish_time": {"order": "desc"}})
        s = s[from_ : from_ + size]
        s = s.highlight(*fields, pre_tags="<em>", post_tags="</em>")

        response = s.execute()
        hits = []
        highlight = {}
        for hit in response:
            src = hit.to_dict()
            hits.append(src)
            if hasattr(hit.meta, "highlight"):
                highlight[hit.meta.id] = {
                    f: list(v) for f, v in hit.meta.highlight.to_dict().items()
                }

        return {
            "total": response.hits.total.value,
            "hits": hits,
            "highlight": highlight,
        }


# 默认单例，供直接 import 使用
es_client = ElasticsearchClient()
news_store = NewsESStore(es_client)
