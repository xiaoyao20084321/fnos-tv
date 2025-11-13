import os
import configparser
from flask_caching import Cache

cache = Cache()

fnos_url = os.environ.get("FNOS_URL", 'http://localhost:5666')
config = configparser.ConfigParser(interpolation=None)
current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir,'data', 'config.ini')
if not os.path.exists(config_path):
    with open(config_path, "w", encoding='utf-8') as configfile:
        configfile.write('''# config.ini
[FNOS]
# 飞牛系统账号
username =
# 飞牛系统密码
password =

[BILIBILI]
# B站cookie，必须有SESSDATA 字段
cookie = ''')
config.read(config_path, encoding='utf-8')
fn_config = config['FNOS']
fnos_username = fn_config.get("username")
if not fnos_username:
    fnos_username = None
fnos_password = fn_config.get("password")
if not fnos_password:
    fnos_password = None
