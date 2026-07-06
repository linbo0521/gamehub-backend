# Python Flask 后端镜像
FROM python:3.11-slim

WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY app.py .
COPY passenger_wsgi.py .

# 创建头像目录
RUN mkdir -p /app/avatars

# 暴露端口（Zeabur 会自动识别）
EXPOSE 8080

# 启动应用
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--timeout", "120", "passenger_wsgi:application"]