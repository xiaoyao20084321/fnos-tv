import requests
from flask import Blueprint, request

import Config
from Config import fnos_username, fnos_password
from Fuction import merge_skipped_segments, calculate_repeat_rate, find_skipped_segments, generate_signature
from core import alist_api
from core.Fnos import FnOs
from core.db.base import CRUDBase
from core.db.model.recordDb import RecordDb
from core.db.model.videoConfigDb import videoConfigList, videoConfigUrl

play = Blueprint('play', __name__, url_prefix='/play')
if fnos_username is not None or fnos_password is not None:
    FnOs.fn_os_ws.start()
    FnOs.login(fnos_username, fnos_password)

api_app = Blueprint('api', __name__, url_prefix='/api')


@api_app.before_request
def before_request():
    if 'getFnUrl' not in request.path:
        url = Config.fnos_url + '/v/api/v1/user/info'
        sign = generate_signature({
            'method': "get",
            'url': '/v/api/v1/user/info'
        }, "16CCEB3D-AB42-077D-36A1-F355324E4237")
        res = requests.get(url, headers={
            'authx': sign,
            'authorization': request.headers.get('authorization')
        })
        if res.json().get('code') != 0:
            return {
                "code": -1,
                "msg": '未登录'
            }


@api_app.get('/skipList')
def skip_list():
    data = request.args
    guid = data.get("guid")
    record_db = CRUDBase(RecordDb)
    # record_data_list = record_db.session.query(record_db.model).filter(RecordDb.guid==guid).group_by(RecordDb.episode_guid).all()
    record_data_dict = record_db.group_by('episode_guid', guid=guid)
    skipped_segments = {}
    for key, value in record_data_dict.items():
        skipped_segments[key] = find_skipped_segments(value)
    ret_data = []
    if len(skipped_segments) >= 3:
        success_data = calculate_repeat_rate(skipped_segments)
        for item in success_data:
            ret_data += item['data']

    return {
        'code': 0,
        'data': merge_skipped_segments(ret_data)
    }


@api_app.get('/getFnUrl')
def get_fn_url():
    _fnos_url = Config.fnos_url
    if _fnos_url.endswith("/"):
        _fnos_url = _fnos_url[:-1]
    return _fnos_url


@api_app.get('/videoConfig')
def get_video_config():
    episode_guid = request.args.get('episode_guid')
    guid = request.args.get('guid')
    if guid is None or episode_guid is None:
        return {
            'code': 404,
            'msg': '未获取到数据'
        }
    ret_data = {
        "list": [],
        "url": []
    }
    for data in [['list', videoConfigList], ['url', videoConfigUrl]]:
        db = CRUDBase(data[1])
        if data[0] == "list":
            _guid = guid
        else:
            _guid = episode_guid
        db_data = db.filter(guid=_guid)
        for item in db_data:
            ret_data[data[0]].append(item.get_data())
    return ret_data


@api_app.post('/videoConfig')
def update_video_config():
    episode_guid = request.args.get('episode_guid')
    guid = request.args.get('guid')
    if guid is None and episode_guid is None:
        return {
            'code': 404,
            'msg': '未获取到guid'
        }
    data = request.json
    db_type = {
        'list': videoConfigList,
        'url': videoConfigUrl,
    }
    for key, value in data.items():
        parent_guid = None
        db = CRUDBase(db_type[key])
        if key == "list":
            _guid = guid
        else:
            _guid = episode_guid
            parent_guid = guid
        for item in value:
            if parent_guid is not  None:
                item['parent_guid'] = parent_guid
            db.add(guid=_guid, **item)
    return {
        'code': 0,
        "msg": 'ok'
    }


@api_app.get('/play')
def _play():
    if fnos_username is None or fnos_password is None:
        return {
            'code': -1,
            "msg": '未获取到飞牛系统账号密码，不做处理'
        }
    play_path = request.args.get('path')
    mountmgr_list = FnOs.mountmgr_list()
    rsps = mountmgr_list.get('rsp', [])
    cloud_config = [rsp for rsp in rsps if rsp.get('mountPoint') in play_path]
    if not cloud_config:
        return {
            "code": -1,
            'msg': '未获取到对应远程挂载信息'
        }
    cloud_config = cloud_config[0]
    if '/dav' not in cloud_config.get('path'):
        return {
            "code": -1,
            'msg': '此远程疑似非alist'
        }
    alist_api.alist_host = f'{cloud_config.get("proto")}://{cloud_config.get("address")}:{cloud_config.get("port")}'
    login_res = alist_api.login(cloud_config.get('userName'), cloud_config.get('password'))
    alist_api.alist_token = login_res.json().get('data', {}).get('token')
    alist_path = cloud_config.get("path").replace('/dav', '') + play_path.replace(cloud_config.get('mountPoint'), '')
    fs_res = alist_api.fs_get(alist_path)
    return {
        'code': 0,
        'data': fs_res.json().get('data', {}).get('raw_url'),
        'msg': '获取成功'
    }
