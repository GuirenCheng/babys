FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 先拷贝依赖单独安装，便于利用构建缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# 通过 entrypoint.py 启动：先向 Consul 注册服务，再拉起 gunicorn，退出时注销
CMD ["python", "entrypoint.py"]
