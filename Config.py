import os
import configparser

fnos_url = os.environ.get("FNOS_URL", 'http://localhost:5666')
config = configparser.ConfigParser(interpolation=None)

# 确保配置文件存在并包含所有必要的段
def ensure_config_file():
    config_path = "./data/config.ini"
    config_exists = os.path.exists(config_path)
    
    if config_exists:
        # 读取现有配置
        config.read(config_path, encoding='utf-8')
    
    # 检查并添加缺失的配置段
    config_updated = False
    
    if not config.has_section('FNOS'):
        config.add_section('FNOS')
        config.set('FNOS', '# 飞牛系统账号', '')
        config.set('FNOS', 'username', '')
        config.set('FNOS', '# 飞牛系统密码', '')
        config.set('FNOS', 'password', '')
        config_updated = True
    
    if not config.has_section('BILIBILI'):
        config.add_section('BILIBILI')
        config.set('BILIBILI', '# B站cookie，必须有SESSDATA 字段', '')
        config.set('BILIBILI', 'cookie', '')
        config_updated = True
    
    # 删除与 dandanplay 相关的视频源配置段
    
    # 如果配置有更新或文件不存在，写入文件
    if config_updated or not config_exists:
        with open(config_path, 'w', encoding='utf-8') as configfile:
            configfile.write('''# config.ini
[FNOS]
# 飞牛系统账号
username =
# 飞牛系统密码
password =

[BILIBILI]
# B站cookie，必须有SESSDATA 字段
cookie = ''')
        # 重新读取配置文件
        config.read(config_path, encoding='utf-8')

ensure_config_file()
fn_config = config['FNOS']
fnos_username = fn_config.get("username")
if not fnos_username:
    fnos_username = None
fnos_password = fn_config.get("password")
if not fnos_password:
    fnos_password = None

# 移除 dandanplay 的视频源配置导出
