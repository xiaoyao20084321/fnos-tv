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
    except Exception as e:
        return {
            "code": -1,
            "msg": '解析参数失败'
        }
    all_danmu_data = {}
    if url is None:
        if episode_number:
            episode_number = int(episode_number)
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
    else:
        danmu_data: RetDanMuType = download_barrage(url)
        return danmu_data.list


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


# 创建表
Base.metadata.create_all(engine)
if __name__ == '__main__':
    app.run()
