#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试Celery定时任务配置
"""

import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'analysis_app.settings')
django.setup()

from analysis_app.celery import app

def test_celery_config():
    """测试Celery配置"""
    print("=== Celery配置测试 ===")
    
    # 测试Celery应用
    print(f"1. Celery应用名称: {app.main}")
    print(f"2. Broker URL: {app.conf.broker_url}")
    print(f"3. Result Backend: {app.conf.result_backend}")
    
    # 测试定时任务配置
    if hasattr(app.conf, 'beat_schedule') and app.conf.beat_schedule:
        print("4. 定时任务配置:")
        for task_name, task_config in app.conf.beat_schedule.items():
            print(f"   - {task_name}: {task_config}")
    else:
        print("4. 未找到定时任务配置")
    
    # 测试任务注册
    print("5. 注册的任务:")
    registered_tasks = app.tasks.keys()
    for task_name in registered_tasks:
        if 'get_project_data_sync' in task_name:
            print(f"   - {task_name}")
    
    print("=== 测试完成 ===")

if __name__ == "__main__":
    test_celery_config()