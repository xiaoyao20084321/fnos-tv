import logging

from flask import Flask

from apps.api import api_app
from apps.danmu.app import danmu
from apps.fnos.app import fnos_app
from core.db.db import engine
from core.db.model import Base

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

app.register_blueprint(danmu, url_prefix='/danmu')
app.register_blueprint(fnos_app, url_prefix='/fnos')
app.register_blueprint(api_app, url_prefix='/api')

# 创建表
Base.metadata.create_all(engine)
import os

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', debug=debug_mode)
