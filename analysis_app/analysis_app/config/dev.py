import os
from pathlib import Path
from urllib.parse import quote_plus

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
CELERY_WORKER_CONCURRENCY = 20
CELERY_WORKER_PREFETCH_MULTIPLIER = 20
CELERY_WORKER_MAX_TASKS_PER_CHILD = 100
CELERY_TASK_ALWAYS_EAGER = False
CELERY_WORKER_DISABLE_RATE_LIMITS = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Timezone configuration
CELERY_TIMEZONE = "Asia/Shanghai"
CELERY_ENABLE_UTC = False
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
