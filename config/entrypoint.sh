#!/bin/bash

# 确保日志目录存在
mkdir -p /app/data/log

# 确保数据库目录有正确的权限
chown -R www-data:www-data /app/data
chmod -R 755 /app/data

# 替换 Nginx 配置中的变量
envsubst '${FNOS_URL}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

if [ "$RUN_AND_UPDATE_WEB" = "true" ]; then
    echo "Starting a.py script..."
    python /app/update_dist.py
fi

# 启动 supervisord（Nginx + Gunicorn）
exec "$@"
