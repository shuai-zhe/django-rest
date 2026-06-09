# tasks包初始化文件
# 使tasks目录成为有效的Python包，便于Celery自动发现任务

# 显式导入任务模块，确保Celery能够正确发现任务
from . import sync