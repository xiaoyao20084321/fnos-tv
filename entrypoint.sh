#!/bin/bash

# 替换 Nginx 配置中的变量
envsubst '${FNOS_URL}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf


if [ "$RUN_AND_UPDATE_WEB" = "true" ]; then
    echo "Starting a.py script..."
    python /app/update_dist.py
fi
# 启动 supervisord（Nginx + Gunicorn）
exec "$@"
