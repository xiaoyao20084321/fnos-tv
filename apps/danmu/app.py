import importlib
import pkgutil

from loguru import logger
from concurrent.futures import ThreadPoolExecutor

from flask import Blueprint
from flask import request

from Fuction import get_platform_link, douban_select, douban_get_first_url
from core.danmu.base import GetDanmuBase
from core.danmu.danmuType import RetDanMuType
import core.danmu as danmu_base

from core.db.base import CRUDBase
from core.db.model.videoConfigDb import videoConfigUrl

danmu = Blueprint('alist', __name__, url_prefix='/danmu')
# 遍历 your_package 中所有子模块
for finder, mod_name, ispkg in pkgutil.walk_packages(danmu_base.__path__, danmu_base.__name__ + "."):
    importlib.import_module(mod_name)


def download_barrage(_url):
    # while True:
    for c in GetDanmuBase.__subclasses__():
        if c.domain in _url:
            d = c().get(_url)
            if d:
                return d


def fetch_emoji(url):
    """获取单个URL的表情数据"""
    try:
        for c in GetDanmuBase.__subclasses__():
            if c.domain in url:
                return {"url": url, "data": c().getImg(url)}
        return {"url": url, "data": []}
    except Exception as e:
        logger.error(f"获取表情失败 {url}: {str(e)}")
        return {"url": url, "data": []}


def fetch_danmu(url, episode_key):
    """获取单个URL的弹幕数据"""
    try:
        logger.info(f"获取弹幕: {url} (集数: {episode_key})")
        danmu_data = download_barrage(url)
        return {"key": episode_key, "data": danmu_data}
    except Exception as e:
        logger.error(f"获取弹幕失败 {url}: {str(e)}")
        return {"key": episode_key, "data": None}


def get_url_dict(douban_id, title, season_number, episode_number, season, guid):
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
        if douban_id is None and (title is not None) and season_number is not None or (
                douban_id and season_number and season_number != '1'):  # 没有豆瓣ID，需要程序匹配
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
    return url_dict


@danmu.get('/get')
def get_danmu():
    try:
        douban_id = request.args.get('douban_id')
        douban_id = None if douban_id == "" or douban_id is None or douban_id == 'undefined' else douban_id
        episode_number = request.args.get('episode_number')
        title = request.args.get('title')
        season_number = request.args.get('season_number')
        season = True if request.args.get('season') == 'true' else False
        url = request.args.get('url')
        guid = request.args.get('guid')
        _type = request.args.get('type', 'json')
    except Exception as e:
        return {
            "code": -1,
            "msg": '解析参数失败'
        }

    if url is not None and url != "":
        danmu_data: RetDanMuType = download_barrage(url)
        if _type == 'json':
            return [item.__dict__() for item in danmu_data.list]
        else:
            return danmu_data.xml

    all_danmu_data = {}
    url_dict = get_url_dict(douban_id, title, season_number, episode_number, season, guid)

    # 准备任务列表
    tasks = []
    for k, v in url_dict.items():
        for u in v:
            tasks.append((u, k))

    # 使用线程池并行获取所有弹幕
    if tasks:
        logger.info(f"开始并行获取 {len(tasks)} 个链接的弹幕")
        with ThreadPoolExecutor(max_workers=min(20, len(tasks))) as executor:
            results = list(executor.map(lambda args: fetch_danmu(*args), tasks))

            # 处理结果
            for result in results:
                if result["data"] is not None:
                    k = result["key"]
                    if k not in all_danmu_data.keys():
                        all_danmu_data[k] = []
                    all_danmu_data[k] += result["data"].list
    # 对数据进行排序
    for key, value in all_danmu_data.items():
        value.sort(key=lambda x: x.time)
        if _type == 'xml':
            all_danmu_data[key] = RetDanMuType(value).xml
        else:
            all_danmu_data[key] = [item.__dict__() for item in value.list]

    return all_danmu_data


@danmu.get('/getEmoji')
def get_emoji():
    try:
        douban_id = request.args.get('douban_id')
        episode_number = request.args.get('episode_number')
        title = request.args.get('title')
        season_number = request.args.get('season_number')
        season = True if request.args.get('season') == 'true' else False
        url = request.args.get('url')
        guid = request.args.get('guid')
        _type = request.args.get('type', 'json')
    except Exception as e:
        return {
            "code": -1,
            "msg": '解析参数失败'
        }

    if url is not None and url != "":
        url_dict = {
            "1": url
        }
    else:
        url_dict = get_url_dict(douban_id, title, season_number, episode_number, season, guid)
    emoji_data = {}

    # 获取所有需要处理的URL
    urls = url_dict.get(list(url_dict.keys())[0], [])

    # 使用线程池并行获取所有表情
    if urls:
        logger.info(f"开始并行获取 {len(urls)} 个链接的表情")
        with ThreadPoolExecutor(max_workers=min(10, len(urls))) as executor:
            all_emoji_data = list(executor.map(fetch_emoji, urls))

            # 处理结果
            for result in all_emoji_data:
                if result["data"]:
                    for d in result["data"]:
                        emoji_data[d['emoji_code']] = d['emoji_url']

    return emoji_data
