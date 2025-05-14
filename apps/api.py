from flask import Blueprint, request

import Config
from Fuction import merge_skipped_segments, calculate_repeat_rate, find_skipped_segments
from core.db.base import CRUDBase
from core.db.model.recordDb import RecordDb
from core.db.model.videoConfigDb import videoConfigList, videoConfigUrl

api_app = Blueprint('fnos', __name__, url_prefix='/api')


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
        db = CRUDBase(db_type[key])
        if key == "list":
            _guid = guid
        else:
            _guid = episode_guid
        for item in value:
            db.add(guid=_guid, **item)
    return {
        'code': 0,
        "msg": 'ok'
    }
