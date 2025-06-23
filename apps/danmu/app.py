import importlib
import pkgutil
import re
from typing import List

from loguru import logger
from concurrent.futures import ThreadPoolExecutor

from flask import Blueprint
from flask import request
from flask import Response

from Fuction import get_platform_link, douban_select, douban_get_first_url, resolve_url_query
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


def other2http(platform_url_list: List[str]):
    ret_list = []
    for url in platform_url_list:
        if not url.startswith("http"):
            agreement = re.findall("^(.*?):", url)
            query = resolve_url_query(url)
            match agreement:
                case ['txvideo']:
                    url = f'https://v.qq.com/x/cover/{query.get("cid")[0]}/{query.get("vid")[0]}.html'
                case ["iqiyi"]:
                    url = f'http://www.iqiyi.com?tvid={query.get("tvid")[0]}'
        ret_list.append(url)
    return ret_list


def fetch_danmu(url, episode_key):
    """获取单个URL的弹幕数据"""
    try:
        logger.info(f"获取弹幕: {url} (集数: {episode_key})")
        danmu_data = download_barrage(url)
        return {"key": episode_key, "data": danmu_data}
    except Exception as e:
        logger.error(f"获取弹幕失败 {url}: {str(e)}")
        return {"key": episode_key, "data": None}


def get_url_dict(douban_id, title=None, season_number=None, episode_number=None, season=None, guid=None, episode_title=None):
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
        # 处理豆瓣的特殊链接，有些如iqiyi:\/\/mobile\/player?aid=225041201&tvid=9749815600&ftype=27&subtype=333转为http协议
        platform_url_list = other2http(douban_get_first_url(douban_id))
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

    if str(episode_number) in url_dict or episode_title in url_dict:
        url_list = url_dict.get(str(episode_number), url_dict.get(episode_title, []))
        if guid is not None:
            # 如果匹配到直接保存到数据库内
            db = CRUDBase(videoConfigUrl)
            for item in url_list:
                db.add(guid=guid, url=item)
        url_dict = {
            episode_number: url_list
        }
    return url_dict


@danmu.get('/get')
def get_danmu():
    try:
        douban_id = request.args.get('douban_id')
        douban_id = None if douban_id == "" or douban_id is None or douban_id == 'undefined' else douban_id
        episode_number = request.args.get('episode_number')
        episode_title = request.args.get('episode_title')
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
        danmu_data.list.sort(key=lambda x: x.time)
        if _type == 'json':
            return [item.__dict__() for item in danmu_data.list]
        else:
            return danmu_data.xml

    all_danmu_data = {}
    url_dict = get_url_dict(douban_id, title, season_number, episode_number, season, guid, episode_title)

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
            all_danmu_data[key] = [item.__dict__() for item in value]

    return all_danmu_data


@danmu.get('/getEmoji')
def get_emoji():
    try:
        douban_id = request.args.get('douban_id')
        douban_id = None if douban_id == "" or douban_id is None or douban_id == 'undefined' else douban_id
        episode_number = request.args.get('episode_number')
        episode_title = request.args.get('episode_title')
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

    if url is not None and url != "":
        url_dict = {
            "1": url
        }
    else:
        url_dict = get_url_dict(douban_id, title, season_number, episode_number, season, guid, episode_title)
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

@danmu.get('/download')
def download_danmu():
    try:
        url = request.args.get('url')
        if not url:
            return {
                "code": -1,
                "msg": '缺少url参数'
            }
    except Exception as e:
        return {
            "code": -1,
            "msg": '解析参数失败'
        }

    # 默认文件名
    filename = 'danmu.xml'
    
    # 获取弹幕数据并下载
    danmu_data: RetDanMuType = download_barrage(url)
    if danmu_data:
        danmu_data.list.sort(key=lambda x: x.time)
        xml_content = danmu_data.xml
        response = Response(xml_content, mimetype='application/xml')
        response.headers.set('Content-Disposition', f'attachment; filename={filename}')
        return response
    
    # 如果没有找到任何弹幕数据，返回空的XML
    empty_xml = '''<?xml version="1.0" encoding="utf-8"?>
<i>
</i>'''
    response = Response(empty_xml, mimetype='application/xml')
    response.headers.set('Content-Disposition', f'attachment; filename={filename}')
    return response

