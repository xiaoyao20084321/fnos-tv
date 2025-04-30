import logging
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

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


def fetch_danmu(url, episode_key):
    """获取单个URL的弹幕数据"""
    try:
        print(f"获取弹幕: {url} (集数: {episode_key})")
        danmu_data = download_barrage(url)
        return {"key": episode_key, "data": danmu_data}
    except Exception as e:
        app.logger.error(f"获取弹幕失败 {url}: {str(e)}")
        return {"key": episode_key, "data": None}


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
        db = CRUDBase(videoConfigUrl)
        for item in db.filter(guid=guid):
            if _episode_number not in url_dict:
                url_dict[_episode_number] = []
            url_dict[_episode_number].append(item.url)
    if len(url_dict.keys()) == 0:
        if season_number != '1' or douban_id == 'undefined':
            douban_data = douban_select(title, season_number, season)
            douban_id = douban_data['target_id']
        platform_url_list = douban_get_first_url(douban_id)
        for platform_url in platform_url_list:
            for c in GetDanmuBase.__subclasses__():
                if c.domain in platform_url:
                    d = c().get_episode_url(platform_url)
                    for k, v in d.items():
                        if k not in url_dict.keys():
                            url_dict[str(k)] = []
                        url_dict[str(k)].append(v)
    if len(url_dict.keys()) == 0:
        url_dict = get_platform_link(douban_id)

    if episode_number is not None and str(episode_number) in url_dict:
        if guid is not None:
            # 如果匹配到直接保存到数据库内
            db = CRUDBase(videoConfigUrl)
            for item in url_dict[f'{episode_number}']:
                db.add(guid=guid, url=item)
        url_dict = {
            episode_number: url_dict[f'{episode_number}']
        }

    all_danmu_data = {}

    # 准备任务列表
    tasks = []
    for k, v in url_dict.items():
        for u in v:
            tasks.append((u, k))

    # 使用线程池并行获取所有弹幕
    if tasks:
        print(f"开始并行获取 {len(tasks)} 个链接的弹幕")
        with ThreadPoolExecutor(max_workers=min(20, len(tasks))) as executor:
            results = list(executor.map(lambda args: fetch_danmu(*args), tasks))

            # 处理结果
            for result in results:
                if result["data"] is not None:
                    k = result["key"]
                    if k in all_danmu_data.keys():
                        all_danmu_data[k] += result["data"].list
                    else:
                        all_danmu_data[k] = result["data"].list
    # 对数据进行排序
    for key, value in all_danmu_data.items():
        value.sort(key=lambda x: x.get('time'))

    return all_danmu_data


def fetch_emoji(url):
    """获取单个URL的表情数据"""
    try:
        for c in GetDanmuBase.__subclasses__():
            if c.domain in url:
                return {"url": url, "data": c().getImg(url)}
        return {"url": url, "data": []}
    except Exception as e:
        app.logger.error(f"获取表情失败 {url}: {str(e)}")
        return {"url": url, "data": []}


@app.route('/danmu/getEmoji')
def get_emoji():
    douban_id = request.args.get('douban_id')
    url_dict = get_platform_link(douban_id)
    emoji_data = {}

    # 获取所有需要处理的URL
    urls = url_dict.get('1', [])

    # 使用线程池并行获取所有表情
    if urls:
        print(f"开始并行获取 {len(urls)} 个链接的表情")
        with ThreadPoolExecutor(max_workers=min(10, len(urls))) as executor:
            all_emoji_data = list(executor.map(fetch_emoji, urls))

            # 处理结果
            for result in all_emoji_data:
                if result["data"]:
                    for d in result["data"]:
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


# 创建表
Base.metadata.create_all(engine)
if __name__ == '__main__':
    app.run()
