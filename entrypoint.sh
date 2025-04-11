#!/bin/bash

# 替换 Nginx 配置中的变量
envsubst '${FNOS_URL}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# 启动 supervisord（Nginx + Gunicorn）
exec "$@"
