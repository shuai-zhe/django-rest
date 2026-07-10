#!/bin/bash

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
