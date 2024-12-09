FROM python:3.9

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY requirements.txt .
COPY src/ ./src/

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 运行应用
CMD ["python", "src/main.py"] 