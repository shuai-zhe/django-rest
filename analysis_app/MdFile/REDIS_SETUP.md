# Redis配置说明

## 配置概述

本项目已配置Redis作为缓存和会话存储后端。配置位于 `analysis_app/settings.py` 文件中。

## 默认配置（已配置连接池）

```python
# Redis Configuration
REDIS_HOST = 'localhost'  # Redis服务器地址
REDIS_PORT = 6379         # Redis端口
REDIS_DB = 0              # Redis数据库编号
REDIS_PASSWORD = None     # Redis密码（如果没有设置为None）

# 缓存配置（已配置连接池）
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PASSWORD': REDIS_PASSWORD,
            'SOCKET_CONNECT_TIMEOUT': 5,  # 连接超时时间（秒）
            'SOCKET_TIMEOUT': 5,          # 操作超时时间（秒）
            # 连接池配置
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 100,           # 最大连接数
                'retry_on_timeout': True,         # 超时重试
                'socket_keepalive': True,         # 保持连接活跃
                'socket_keepalive_options': {     # 保持连接选项
                    'TCP_KEEPIDLE': 60,          # 空闲60秒后开始发送keepalive
                    'TCP_KEEPINTVL': 30,         # 每30秒发送一次keepalive
                    'TCP_KEEPCNT': 3,            # 最多重试3次
                },
            },
            # 序列化器配置
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        },
        'KEY_PREFIX': 'analysis_app',     # 缓存键前缀
    }
}
```

### 连接池配置说明

- **max_connections**: 连接池最大连接数，根据应用并发量调整
- **retry_on_timeout**: 连接超时时自动重试
- **socket_keepalive**: 保持TCP连接活跃，避免频繁重建连接
- **序列化器**: 使用JSON序列化，支持复杂数据结构
- **压缩器**: 使用zlib压缩，减少网络传输数据量

# 会话存储配置
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

## 环境变量配置（推荐）

对于生产环境，建议使用环境变量配置Redis连接：

```python
import os

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
```

## 安装Redis服务器

### Windows
1. 下载Redis for Windows: https://github.com/microsoftarchive/redis/releases
2. 解压并运行 `redis-server.exe`
3. 或者使用WSL2安装Redis

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### macOS
```bash
brew install redis
brew services start redis
```

## 测试Redis连接

运行测试脚本验证Redis配置：

```bash
python test_redis.py
```

## 基本使用方法

### 1. 使用Django缓存API

```python
from django.core.cache import cache

# 设置缓存
cache.set('key', 'value', timeout=3600)  # 缓存1小时

# 获取缓存
value = cache.get('key')

# 删除缓存
cache.delete('key')

# 检查缓存是否存在
if cache.has_key('key'):
    print("缓存存在")
```

### 2. 缓存项目数据示例

```python
from django.core.cache import cache

# 缓存项目数据
project_data = {
    'name': '项目名称',
    'price_dict': {'SPOT': 100.0, 'FUTURES': 105.0},
    'volume_dict': {'SPOT': 50000, 'FUTURES': 30000}
}

# 使用缓存键前缀和项目ID
cache_key = f"project:1:data"
cache.set(cache_key, project_data, timeout=3600)
print("✅ 项目数据已缓存")

# 获取缓存数据
cached_data = cache.get(cache_key)
if cached_data:
    print("✅ 从缓存获取项目数据")
else:
    print("⚠️ 项目数据未在缓存中找到")
```

### 3. 缓存API响应

```python
from django.core.cache import cache

# 缓存API响应
api_params = {'currency_pair': 'BTC_USDT', 'interval': '15m'}
api_response = {'status': 'success', 'data': [...]}

# 生成基于参数的缓存键
param_str = str(sorted(api_params.items()))
cache_key = f"api:get_kline:{hash(param_str)}"

cache.set(cache_key, api_response, timeout=1800)
print("✅ API响应已缓存")

# 获取缓存响应
cached_response = cache.get(cache_key)
if cached_response:
    print("✅ 从缓存获取API响应")
```

## 高级配置选项

### 连接池配置

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://localhost:6379/0',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 100,
                'retry_on_timeout': True,
            },
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
            'SOCKET_KEEPALIVE': True,
        }
    }
}
```

### 多个缓存后端

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://localhost:6379/0',
    },
    'session': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://localhost:6379/1',
    },
}
```

## 常见问题

### 1. 连接失败
- 检查Redis服务是否启动
- 确认主机名和端口是否正确
- 检查防火墙设置

### 2. 认证失败
- 确认Redis密码是否正确
- 检查requirepass配置

### 3. 性能优化
- 使用连接池减少连接开销
- 合理设置缓存超时时间
- 使用适当的序列化器

## 监控和维护

### Redis CLI命令

```bash
# 连接Redis
redis-cli

# 查看信息
info

# 查看内存使用
info memory

# 查看键数量
dbsize

# 清空当前数据库
flushdb

# 清空所有数据库
flushall
```

### Python监控

```python
import redis

r = redis.Redis(host='localhost', port=6379, db=0)
print(r.info())  # 获取Redis信息
```

## 安全建议

1. 生产环境务必设置Redis密码
2. 使用非默认端口
3. 配置防火墙限制访问
4. 定期备份重要数据
5. 监控Redis内存使用情况

---

更多详细信息请参考：[Django Redis文档](https://github.com/jazzband/django-redis)