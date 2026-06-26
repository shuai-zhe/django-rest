FROM python:3.10.0-slim

WORKDIR /app

# 先复制依赖文件，利用 Docker 层缓存
COPY requirements.txt /app/

# 安装依赖并清理缓存，减小镜像体积
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . /app

EXPOSE 5001

CMD ["python", "manage.py", "runserver", "0.0.0.0:5001"]

