#!/bin/bash

# MySQL 首次初始化脚本：在容器启动时自动创建绑定的数据库和账号。
# 通过 docker-entrypoint-initdb.d 挂载，仅在数据卷为空时执行一次。
set -e

# 若环境变量不存在则给出默认值
MYSQL_DATABASE="${MYSQL_DATABASE:-analysis_app}"
MYSQL_USER="${MYSQL_USER:-analysis}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-analysis123456}"

mysql --protocol=socket -uroot -p"$MYSQL_ROOT_PASSWORD" <<-EOSQL
  CREATE DATABASE IF NOT EXISTS \`${MYSQL_DATABASE}\`
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

  CREATE USER IF NOT EXISTS '${MYSQL_USER}'@'%' IDENTIFIED BY '${MYSQL_PASSWORD}';
  GRANT ALL PRIVILEGES ON \`${MYSQL_DATABASE}\`.* TO '${MYSQL_USER}'@'%';
  ALTER USER '${MYSQL_USER}'@'%' IDENTIFIED BY '${MYSQL_PASSWORD}';
  FLUSH PRIVILEGES;
EOSQL

echo "Database '${MYSQL_DATABASE}' and user '${MYSQL_USER}' are ready."


# Django 数据库迁移
echo "Running Django migrations..."
python manage.py migrate
python manage.py makemigrations
python manage.py migrate


# Celery Beat 启动
echo "Starting Celery Beat..."
celery -A analysis_app beat --loglevel=info &

# Celery Worker 启动
echo "Starting Celery Worker..."
celery -A analysis_app worker --loglevel=info &

# Django Shell (进入交互模式)
echo "Starting Django Shell..."
python manage.py runserver 0.0.0.0:5001
