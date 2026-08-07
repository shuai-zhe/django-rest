FROM python:3.10.0-slim

WORKDIR /app

# 先复制依赖文件，利用 Docker 层缓存
COPY requirements.txt /app/
COPY deploy_file/.env /app/
# 安装依赖并清理缓存，减小镜像体积
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn && pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn

# 复制项目代码
COPY . /app

EXPOSE 5001

CMD ["bash","deploy_file/start.sh"]
