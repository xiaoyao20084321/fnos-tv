import os
import configparser

fnos_url = os.environ.get("FNOS_URL", 'http://localhost:5666')
config = configparser.ConfigParser(interpolation=None)
if not os.path.exists("./data/config.ini"):
    with open("./data/config.ini", "w", encoding='utf-8') as configfile:
        configfile.write('''# config.ini
[FNOS]
# 飞牛系统账号
username =
# 飞牛系统密码
password =

[BILIBILI]
# B站cookie，必须有SESSDATA 字段
cookie = ''')
config.read('./data/config.ini', encoding='utf-8')
fn_config = config['FNOS']
fnos_username = fn_config.get("username")
if not fnos_username:
    fnos_username = None
fnos_password = fn_config.get("password")
if not fnos_password:
    fnos_password = None
