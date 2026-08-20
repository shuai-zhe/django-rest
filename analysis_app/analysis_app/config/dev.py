import os
from pathlib import Path
from urllib.parse import quote_plus

from elasticsearch_dsl import connections as es_connections

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# Mysql Configuration
MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = os.environ.get("MYSQL_PORT", 3306)
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "analysis_app")
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "123456")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": MYSQL_DATABASE,
        "USER": MYSQL_USER,
        "PASSWORD": MYSQL_PASSWORD,
        "HOST": MYSQL_HOST,
        "PORT": MYSQL_PORT,
    }
}


# Redis Configuration
REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT = os.environ.get("REDIS_PORT", 6379)
REDIS_DB = os.environ.get("REDIS_DB", 0)
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")  # 如果没有密码设置为None


# Cache Configuration
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "PASSWORD": REDIS_PASSWORD,
            "SOCKET_CONNECT_TIMEOUT": 5,  # seconds
            "SOCKET_TIMEOUT": 5,  # seconds
            # 连接池配置
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 100,  # 最大连接数
                "retry_on_timeout": True,  # 超时重试
                "socket_keepalive": True,  # 保持连接活跃
            },
            # 序列化器配置
            "SERIALIZER": "django_redis.serializers.json.JSONSerializer",
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
        },
        "KEY_PREFIX": "analysis_app",
    }
}

# Celery Configuration
CELERY_CONNECT_URL = (
    f"redis://{':'+quote_plus(REDIS_PASSWORD)+'@' if REDIS_PASSWORD else ''}{REDIS_HOST}:{REDIS_PORT}/"
    + "{REDIS_DB}"
)
CELERY_BROKER_URL = CELERY_CONNECT_URL.format(REDIS_DB="7")
CELERY_RESULT_BACKEND = CELERY_CONNECT_URL.format(REDIS_DB="8")
CELERY_WORKER_CONCURRENCY = os.environ.get("CELERY_WORKER_CONCURRENCY", 4)
CELERY_WORKER_PREFETCH_MULTIPLIER = os.environ.get(
    "CELERY_WORKER_PREFETCH_MULTIPLIER", 4
)
CELERY_WORKER_MAX_TASKS_PER_CHILD = os.environ.get(
    "CELERY_WORKER_MAX_TASKS_PER_CHILD", 4
)
CELERY_TASK_ALWAYS_EAGER = False
CELERY_WORKER_DISABLE_RATE_LIMITS = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Timezone configuration
CELERY_TIMEZONE = "Asia/Shanghai"
CELERY_ENABLE_UTC = False
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Elasticsearch Configuration
# 用于存储/检索新闻数据
# 容器内访问宿主机映射端口请用 host.docker.internal（Docker 提供的主机网关）
# 本地直接运行 Django 时可用 127.0.0.1
ES_HOST = os.environ.get("ES_HOST", "host.docker.internal")
ES_PORT = os.environ.get("ES_PORT", 5001)
ES_SCHEME = os.environ.get("ES_SCHEME", "http")
# 多个节点可用逗号分隔，如 "host1:9200,host2:9200"
ES_HOSTS = os.environ.get(
    "ES_HOSTS",
    f"{ES_SCHEME}://{ES_HOST}:{ES_PORT}",
)
# 新闻数据索引名（统一前缀，便于多环境隔离）
ES_NEWS_INDEX = os.environ.get("ES_NEWS_INDEX", "news")
# ES 已关闭安全认证，留空即可；如开启鉴权可在此配置
ES_USERNAME = os.environ.get("ES_USERNAME", "")
ES_PASSWORD = os.environ.get("ES_PASSWORD", "")
ES_TIMEOUT = int(os.environ.get("ES_TIMEOUT", 30))
ES_IK_ANALYZER = {
    "analysis": {
        "analyzer": {
            "ik_max_word": {"type": "ik_max_word"},
            "ik_smart": {"type": "ik_smart"},
        }
    }
}
ES_CONFIG = {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    **ES_IK_ANALYZER,
}
ES_NEWS_START_TIME = "2026-01-01"

# ---------------------------------------------------------------------------
# Elasticsearch 连接注册（方向A：仅用 elasticsearch_dsl，未引入 django_elasticsearch_dsl）
# 集中在本文件书写一次；settings.py 末尾会 import 本模块，故注册早于任何 Document 操作。
# 后续若扩展为 django_elasticsearch_dsl：
#   1) 移除本段 connections.configure；
#   2) 在 INSTALLED_APPS 加入 "django_elasticsearch_dsl"；
#   3) 在下方声明 ELASTICSEARCH_DSL = {"default": {...}} 即可，其余代码无需改动。
# ---------------------------------------------------------------------------

_es_client_cfg = {
    "hosts": ES_HOSTS,
    "timeout": ES_TIMEOUT,
}
if ES_USERNAME and ES_PASSWORD:
    _es_client_cfg["basic_auth"] = (ES_USERNAME, ES_PASSWORD)
es_connections.configure(default=_es_client_cfg)
