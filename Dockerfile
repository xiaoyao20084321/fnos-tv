FROM python:3.12-slim

# 安装必要工具
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      nginx \
      curl \
      jq \
      unzip \
      supervisor \
      gettext-base && \
    rm -rf /var/lib/apt/lists/*

# 创建工作目录
WORKDIR /app

ARG FNOS_URL
ARG RUN_AND_UPDATE_WEB=false
ENV FNOS_URL=${FNOS_URL}
ENV RUN_AND_UPDATE_WEB=${RUN_AND_UPDATE_WEB}

# 复制并安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制 Flask 应用及静态资源
COPY . .

# 复制 nginx 和 supervisor 配置
COPY nginx.conf.template /etc/nginx/nginx.conf.template
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 复制启动脚本
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY update_dist.sh ./update_dist.sh
RUN chmod +x ./update_dist.sh

# 暴露 HTTP 端口
EXPOSE 80

# 启动 supervisor（它会同时拉起 nginx 和 gunicorn）
ENTRYPOINT ["/bin/bash", "-c", "if [ \"$RUN_AND_UPDATE_WEB\" = \"true\" ]; then ./update_dist.sh; fi; exec /entrypoint.sh"]

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
