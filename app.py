import logging

import requests
from flask import Flask, request

import Config
from Config import fnos_url
from Fuction import get_platform_link, douban_select, douban_get_first_url, find_skipped_segments, \
    calculate_repeat_rate, merge_skipped_segments
from Getdanmu import download_barrage, RetDanMuType, GetDanmuBase
from core.db.base import CRUDBase
from core.db.db import engine
from core.db.model import Base
from core.db.model.recordDb import RecordDb
from core.db.model.videoConfigDb import videoConfigList, videoConfigUrl

app = Flask(__name__)
app.logger.setLevel(logging.INFO)


@app.route('/danmu/get')
def main():  # put application's code here
    try:
        douban_id = request.args.get('douban_id')
        episode_number = request.args.get('episode_number')
        title = request.args.get('title')
        season_number = request.args.get('season_number')
        season = True if request.args.get('season') == 'true' else False
        url = request.args.get('url')
        guid = request.args.get('guid')
    except Exception as e:
        return {
            "code": -1,
            "msg": '解析参数失败'
        }
    if url is not None:
        danmu_data: RetDanMuType = download_barrage(url)
        return danmu_data.list
    if episode_number:
        episode_number = int(episode_number)
    url_dict = {}
    if guid is not None and episode_number:
        _episode_number = str(episode_number)
        url_dict = {
            _episode_number: []
        }
        db = CRUDBase(videoConfigUrl)
        for item in db.filter(guid=guid):
            url_dict[_episode_number].append(item.url)
    all_danmu_data = {}
    if len(url_dict.keys()) == 0:
        if season_number != '1' or douban_id == 'undefined':
            douban_data = douban_select(title, season_number, season)
            target_id = douban_data['target_id']
            platform_url_list = douban_get_first_url(target_id)
            url_dict = {}
            for platform_url in platform_url_list:
                for c in GetDanmuBase.__subclasses__():
                    if c.domain in platform_url:
                        d = c().get_episode_url(platform_url)
                        for k, v in d.items():
                            if k not in url_dict.keys():
                                url_dict[k] = []
                            url_dict[k].append(v)
        else:
            url_dict = get_platform_link(douban_id)

    if episode_number is not None:
        url_dict = {
            episode_number: url_dict[f'{episode_number}']
        }

    for k, v in url_dict.items():
        for u in v:
            danmu_data: RetDanMuType = download_barrage(u)
            if k in all_danmu_data.keys():
                all_danmu_data[k] += danmu_data.list
            else:
                all_danmu_data[k] = danmu_data.list
    return all_danmu_data


@app.route('/danmu/getEmoji')
def get_emoji():
    douban_id = request.args.get('douban_id')
    url_dict = get_platform_link(douban_id)
    emoji_data = {}
    for url in url_dict['1']:
        for c in GetDanmuBase.__subclasses__():
            if c.domain in url:
                data = c().getImg(url)
                for d in data:
                    emoji_data[d['emoji_code']] = d['emoji_url']
    return emoji_data


@app.post('/fnos/v/api/v1/play/record')
def record():
    """
    记录播放记录，推算跳过片段
    :return: 
    """
    data = request.json
    # 转发到飞牛原始接口
    res = requests.post(f"{fnos_url}/v/api/v1/play/record", json=data, headers={
        "Cookie": request.headers.get('Cookie'),
        "authorization": request.headers.get('authorization'),
        "authx": request.headers.get('authx'),
    })
    record_db = CRUDBase(RecordDb)
    record_db.add(
        guid=data.get("guid"),
        episode_guid=data.get("item_guid"),
        time=data.get("ts"),
        create_time=data.get("create_time"),
        playback_speed=data.get("playback_speed"),
    )
    return res.json()
    # return 'ok'


@app.get('/api/skipList')
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


@app.get('/api/getFnUrl')
def get_fn_url():
    _fnos_url = Config.fnos_url
    if _fnos_url.endswith("/"):
        _fnos_url = _fnos_url[:-1]
    return _fnos_url


@app.get('/api/videoConfig')
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


@app.post('/api/videoConfig')
def update_video_config():
    episode_guid = request.args.get('episode_guid')
    guid = request.args.get('guid')
    if guid is None:
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


# 创建表
Base.metadata.create_all(engine)
if __name__ == '__main__':
    app.run()
