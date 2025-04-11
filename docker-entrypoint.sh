#!/bin/bash
set -e

if [ "$RUN_AND_UPDATE_WEB" = "true" ]; then
  echo "Updating web dist..."
  ./update_dist.sh || echo "update_dist.sh failed, but continuing..."
fi

# 执行原来的 entrypoint.sh（再由它去执行 gunicorn/nginx 等）
exec /entrypoint.sh
