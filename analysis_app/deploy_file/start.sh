#!/bin/bash

# MySQL 首次初始化脚本：在容器启动时自动创建绑定的数据库和账号。
# 通过 docker-entrypoint-initdb.d 挂载，仅在数据卷为空时执行一次。
set -e
python -c '
#import os
#
#akshare_path = "/usr/local/lib/python3.11/site-packages/akshare/stock_feature/stock_hist_em.py"
#if not os.path.exists(akshare_path):
#    raise Exception("akshare path not found")
#
#OLD = """{"daily": "101", "weekly": "102", "monthly": "103"}"""
#NEW = """{"daily": "101", "weekly": "102", "monthly": "103","5m":"5","15m":"15","30m":"30","1h":"60"}"""
#
#with open(akshare_path, "r", encoding="utf-8") as f:
#    content = f.read()
#
#if OLD not in content:
#    print("[patch] target string not found or already patched, skip")
#else:
#    content = content.replace(OLD, NEW, 1)
#    with open(akshare_path, "w", encoding="utf-8") as f:
#        f.write(content)
#    print("[patch] akshare stock_hist_em.py patched successfully")
'



# Django 数据库迁移
echo "Running Django migrations..."
python manage.py migrate
python manage.py makemigrations
python manage.py migrate


# 启动 Celery 进程守护函数：后台进程异常退出后自动重启，避免容器静默失效
start_celery() {
  while true; do
    echo "[celery-beat] Starting..."
    celery -A analysis_app beat --loglevel=info &
    BEAT_PID=$!

    echo "[celery-worker] Starting..."
    celery -A analysis_app worker --loglevel=info &
    WORKER_PID=$!

    # 等待任一 Celery 进程退出
    wait -n "$BEAT_PID" "$WORKER_PID"
    echo "[celery] One of the celery processes exited, restarting in 3s..."
    # 清理可能残留的进程
    kill "$BEAT_PID" "$WORKER_PID" 2>/dev/null || true
    sleep 3
  done
}

# 后台启动 Celery 守护
start_celery &

# Django Web 服务（前台运行，使用 gunicorn 生产级 WSGI 服务器）
# 使用 exec 使其成为 PID 1，确保 docker stop 等信号能被正确接收，实现优雅关闭
# --workers 根据 CPU 核数调整，--timeout 避免长请求被误杀
echo "Starting Django Web Server (gunicorn) on 0.0.0.0:5001..."
exec gunicorn analysis_app.wsgi:application \
  --bind 0.0.0.0:5001 \
  --workers 4 \
  --worker-class sync \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
