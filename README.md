# Stock & Futures Data Platform
> 基于Django+DRF+Celery构建的多源金融数据采集与查询平台，自研解耦API框架，支持MySQL/ES多存储，Docker容器化部署，前端基于Vue。

## 📚 技术栈
**后端**
- Django 5.2
- DRF (Django Rest Framework)
- Celery 5.6 + django-celery-beat
- MySQL
- Elasticsearch 7.x
- Redis
- Gunicorn

**前端**
- Vue

**部署**
- Docker

## ✨ 核心特性
### 1. 自研DRF解耦框架：Resource层抽象
替代DRF原生ViewSet，重写`dispatch()`实现标准化请求流水线：
`入参校验 → 业务执行 → 出参校验`
业务开发仅需实现`perform_request()`，声明序列化类，消除路由、参数校验大量样板代码。

### 2. 自动化路由注册
基于类反射实现`ResourceRouter`：
自动扫描视图模块内路由声明列表，动态生成`path()`路由。
新增接口**无需修改urls.py**，当前覆盖4个业务模块，共8个接口，接口开发成本降低约60%。

### 3. 统一接口契约 & 查询DSL
- 自定义`APIRenderer` + 全局`exception_handler`，所有接口统一返回结构：
```json
{
  "code": 200,
  "success": true,
  "data": {},
  "message": "success"
}
```

- 自研查询 DSL，支持`filters`/`order_by`，可动态翻译成 ORM 条件 **或 Elasticsearch 查询语句**，支撑前端灵活筛选、排序。

### 4. 多源异步数据采集链路

基于 Celery + `django-celery-beat(DatabaseScheduler)`，托管 5 个定时任务：

- 聚合 6 + 外部数据源：gate、cryptobubbles、AkShare、BaoStock、Panews、MarsBit
- 交易时段感知：非开盘时段自动跳过采集任务
- Redis 实现断点续采，减少无效请求、避免重复抓取

### 5. 分层数据存储架构

- MySQL：存储标的结构化行情数据
- Elasticsearch 7.x：新闻全文检索，按日分索引
- 基于`elasticsearch-dsl`封装`BaseDocument`，手写注册连接逻辑，**替代`django_elasticsearch_dsl`**，Django 主进程与 Celery Worker 均可正常访问 ES。

## 📦 项目能力概述

- ✅ Stock 标的管理、数据采集、同步与异常自动处理
- ✅ 期货模块数据接入、展示、表结构与采集任务
- ✅ 日志采集、多维度筛选排序、多源新闻检索
- ✅ 定时任务管理、任务异常监控、断点续采
- ✅ 标准化 REST 接口，统一返回格式、全局异常捕获

## 🚀 快速启动

> 
> 基于 Docker 部署

```
# 构建并启动所有服务(django/gunicorn,celery,redis,mysql,es)
docker-compose up -d
```

## 📁 模块清单

- stock：证券标的数据模块
- futures：期货数据模块
- gateway：数据源 gate 对接模块
- news：新闻采集与 ES 全文检索模块
