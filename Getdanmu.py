import base64
import hashlib
import json
import re
import time
import traceback
import zlib
from dataclasses import dataclass, field
from typing import List
from urllib.parse import urljoin
from venv import logger
from jsonpath_ng import jsonpath, parse
import concurrent.futures
from functools import partial

import parsel
import xmltodict
from curl_cffi import requests
from retrying import retry
from tqdm import tqdm

from Fuction import request_data, get_md5


@dataclass
class DanMuType:
    text: str = ''  # 弹幕文本
    time: int = 0  # 弹幕时间
    mode: int = 0  # 弹幕模式
    color: str = '#FFFFFF'  # 弹幕颜色
    border: bool = False  # 弹幕是否有描边
    style: dict = field(default_factory=dict)  # 弹幕自定义样式
    other: dict = field(default_factory=dict)  # 其他数据

    def __dict__(self):
        return dict(
            text=self.text.replace('&#', ''),
            time=int(self.time),
            mode=self.mode,
            color=str(self.color) if isinstance(self.color, str) and self.color.startswith(
                "#") else f'#{int(self.color):06X}',
            border=self.border,
            style=self.style
        )

    def escape_xml(self):
        # 定义需要转义的字符及其对应的转义序列
        escape_chars = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&apos;'
        }

        # 按照需要转义的字符顺序进行替换
        for char, escaped_char in escape_chars.items():
            self.text = self.text.replace(char, escaped_char)

        return self.text


@dataclass
class RetDanMuType:
    list: List[DanMuType]
    xml: str


class DataclassJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, DanMuType):
            return obj.__dict__()
        return super().default(obj)


class GetDanmuBase(object):
    base_xml = '''<?xml version="1.0" encoding="utf-8"?>
<i>
{}
</i>'''
    data_list = []
    name = ""
    domain = ""

    def get_data_dict(self) -> DanMuType:
        return DanMuType()

    def request_data(self, session, method, url, status_code=None, **kwargs):
        """
        统一的请求函数，用于网络请求
        :param session: 
        :param method: 
        :param url: 
        :param status_code: 
        :param kwargs: 
        :return: 
        """
        try:
            res = session.request(method, url, **kwargs)
            return res
        except Exception as e:
            logger.error(e)
            return

    def get_link(self, url) -> List:
        return []

    def main(self, links: List) -> List[requests.Response]:
        """
        获取弹幕的主逻辑
        """
        pass

    def parse(self) -> list[DanMuType]:
        """
        解析返回的原始数据
        """
        return []

    def get(self, url, _type='json'):
        self.data_list = []
        try:
            links = self.get_link(url)
            self.main(links)
            parse_data = self.parse()
            return RetDanMuType(json.loads(json.dumps(parse_data, cls=DataclassJSONEncoder)),
                                self.base_xml.format('\n'.join([self.list2xml(d) for d in parse_data])))
        except Exception as e:
            return RetDanMuType([], "")

    def getImg(self, url):
        """
        获取弹幕的表情链接
        """
        return []

    def list2xml(self, data: DanMuType):
        xml_str = f'    <d p="{data.time},{data.mode},{data.style.get("size", 25)},{int(data.color[1:], 16) if isinstance(data.color, str) and data.color.startswith("#") else data.color},0,0,0,0">{data.escape_xml()}</d>'
        return xml_str

    def time_to_second(self, _time: list):
        s = 0
        m = 1
        for d in _time[::-1]:
            s += m * int(d)
            m *= 60
        return s

    def get_episode_url(self, url: str) -> dict[str, str]:
        """
        根据一个链接获取所有剧集链接，返回一个字典
        :param url: 
        :return: 
        """
        return {}


class GetDanmuTencent(GetDanmuBase):
    name = "腾讯视频"
    domain = "v.qq.com"

    def __init__(self):
        self.api_danmaku_base = "https://dm.video.qq.com/barrage/base/"
        self.api_danmaku_segment = "https://dm.video.qq.com/barrage/segment/"

    def get_link(self, url) -> List[str]:
        res = request_data("GET", url)
        res.encoding = res.apparent_encoding
        sel = parsel.Selector(res.text)
        title = sel.xpath('//title/text()').get().split('_')[0]
        vid = re.findall(f'"title":"{title}","vid":"(.*?)"', res.text)
        if vid:
            vid = vid[-1]
        if not vid:
            vid = re.search("/([a-zA-Z0-9]+)\.html", url)
            if vid:
                vid = vid.group(1)
        if not vid:
            logger.error("解析vid失败，请检查链接是否正确")
            return []
        res = request_data("GET", urljoin(self.api_danmaku_base, vid))
        if res.status_code != 200:
            logger.error("获取弹幕详情失败")
            return []
        # 使用线程池并行获取所有分段
        segment_indices = list(res.json().get("segment_index", {}).values())
        links = [urljoin(self.api_danmaku_segment,
                         vid + "/" + item.get("segment_name", "/")) for item in segment_indices]
        return links

    def parse(self):
        data_list = []
        for _data in tqdm(self.data_list):
            data = _data.json()
            for item in data.get("barrage_list", []):
                _d = self.get_data_dict()
                _d.time = int(item.get("time_offset", 0)) / 1000
                _d.text = item.get("content", "")
                _d.other['create_time'] = item.get('create_time', "")
                if item.get("content_style") != "":
                    content_style = json.loads(item.get("content_style"))
                    if content_style.get("color") != "ffffff":
                        _d.color = int(content_style.get("color", "ffffff"), 16)
                data_list.append(_d)
        return data_list

    def main(self, links):
        self.data_list = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(links))) as executor:
            fun = partial(self.request_data, requests, "GET")
            results = list(tqdm(executor.map(fun, links),
                                total=len(links),
                                desc="腾讯视频弹幕获取"))
            self.data_list.extend(results)

        return self.data_list

    def getImg(self, url):
        vid = re.search("/([a-zA-Z0-9]+)\.html", url)
        if vid:
            vid = vid.group(1)
        if not vid:
            return self.error("解析vid失败，请检查链接是否正确")
        cid = url.split('/')[-2]
        data = {
            "vid": vid,
            "cid": cid,
            "lid": "",
            "bIsGetUserCfg": True
        }
        res = request_data("POST",
                           "https://pbaccess.video.qq.com/trpc.danmu.danmu_switch_comm.DanmuSwitch/getVideoDanmuSwitch",
                           json=data)
        danmukey = res.json().get('data', {}).get('registResultInfo', {}).get('dataKey')
        res = request_data("POST", "https://pbaccess.video.qq.com/trpc.message.danmu_richdata.Richdata/GetRichData",
                           json={
                               "danmu_key": danmukey,
                               "vip_degree": 0
                           },
                           headers={
                               'origin': "https://v.qq.com",
                               'referer': "https://v.qq.com",
                           })
        emoji_infos = res.json().get('data', {}).get('emoji_configs', {}).get('emoji_infos', [])
        emoji_data_list = []
        for emoji_info in emoji_infos:
            emoji_data_list.append(
                {
                    'emoji_code': emoji_info.get('emoji_code'),
                    'emoji_url': emoji_info.get('emoji_url'),
                }
            )
        return emoji_data_list

    def get_episode_url(self, url: str) -> dict[str, str]:
        res = request_data("GET", url)
        res.encoding = res.apparent_encoding
        sel = parsel.Selector(res.text)
        title = sel.xpath('//title/text()').get().split('_')[0]
        vid = re.findall(f'"title":"{title}","vid":"(.*?)"', res.text)
        if vid:
            vid = vid[-1]
        if not vid:
            vid = re.search("/([a-zA-Z0-9]+)\.html", url)
            if vid:
                vid = vid.group(1)
        cid = re.findall('"cid":"(.*?)"', res.text)[0]
        if not vid:
            logger.error("解析vid失败，请检查链接是否正确")
            return {}

        url = 'https://pbaccess.video.qq.com/trpc.universal_backend_service.page_server_rpc.PageServer/GetPageData'
        data = {
            "page_params": {
                "req_from": "web_vsite",
                "page_id": "vsite_episode_list",
                "page_type": "detail_operation",
                "id_type": "1",
                "page_size": "",
                "cid": cid,
                "vid": vid,
                "lid": "",
                "page_num": "",
                "page_context": "",
                "detail_page_type": "1"
            },
            "has_cache": 1
        }
        res = request_data("POST", url, json=data, headers={
            'referer': 'https://v.qq.com/',
            'Cookie': 'video_platform=2; vversion_name=8.2.95'
        })
        json_data = res.json().get('data', {})
        data_list = json_data.get("module_list_datas", [{}])[0].get('module_datas', [{}])[0].get('item_data_lists',
                                                                                                 {}).get('item_datas',
                                                                                                         [])
        url_dict = {}
        for item in data_list:
            item_params = item.get('item_params')
            url_dict[f"{item_params.get('album_order')}"] = item_params.get('page_url')
        return url_dict


class GetDanmuBilibili(GetDanmuBase):
    name = "B站"
    domain = "bilibili.com"

    def __init__(self):
        self.api_video_info = "https://api.bilibili.com/x/web-interface/view"
        self.api_epid_cid = "https://api.bilibili.com/pgc/view/web/season"

    def get_link(self, url) -> List[str]:
        if url.find("bangumi/") != -1 and url.find("ep") != -1:
            epid = re.findall("ep(\d+)", url)[0]
            params = {
                "ep_id": epid
            }
            res = request_data("GET", url=self.api_epid_cid, params=params, impersonate="chrome110")
            res_json = res.json()
            if res_json.get("code") != 0:
                logger.error("获取番剧信息失败")
                return []

            target_episode = None
            for episode in res_json.get("result", {}).get("episodes", []):
                if episode.get("id", 0) == int(epid):
                    target_episode = episode
                    break
            if target_episode:
                return [f'https://comment.bilibili.com/{target_episode.get("cid")}.xml']
        return []

    def parse(self):
        data_list = []
        for item in self.data_list:
            xml_data = item.text
            datas = re.findall('<d p="(.*?)">(.*?)<\/d>', xml_data)
            for data in tqdm(datas):
                _d = self.get_data_dict()
                _d.text = data[1]
                data_time = data[0].split(",")
                _mode = int(data_time[1])
                mode = 0
                match _mode:
                    case 1 | 2 | 3:
                        mode = 0
                    case 4:
                        mode = 2
                    case 5:
                        mode = 1

                _d.time = float(data_time[0])
                _d.mode = mode
                _d.style['size'] = data_time[2]
                _d.color = data_time[3]
                data_list.append(_d)
        return data_list

    def main(self, links: List[str]):
        self.data_list = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(links))) as executor:
            fun = partial(self.request_data, requests, "GET", impersonate="chrome110")
            results = list(tqdm(executor.map(fun, links),
                                total=len(links),
                                desc="哔哩哔哩弹幕获取"))
            self.data_list.extend(results)

        return self.data_list

    def get_episode_url(self, url):
        url_dict = {}
        if url.find("bangumi/") != -1 and url.find("ep") != -1:
            epid = re.findall("ep(\d+)", url)[0]
            params = {
                "ep_id": epid
            }
            res = request_data("GET", url=self.api_epid_cid, params=params, impersonate="chrome110")
            res_json = res.json()
            for item in res_json.get('result', {}).get('episodes', []):
                if item.get('section_type') == 0:
                    url_dict[str(item.get('title'))] = item.get('share_url')
        return url_dict


class GetDanmuIqiyi(GetDanmuBase):
    name = "爱奇艺"
    domain = "iqiyi.com"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._req = requests.Session(impersonate="chrome124")

    def request_data_by_iqiyi(self, method, url, *args, **kwargs):
        res = self.request_data(self._req, method, url=url, *args, **kwargs)
        if res.status_code == 200:
            # 解压缩数据
            decompressed_data = zlib.decompress(res.content)
            data = decompressed_data.decode('utf-8')
            data_list = []
            for d in re.findall('<bulletInfo>.*?</bulletInfo>', data, re.S):
                d = d.replace('&#', '')
                d_dict = xmltodict.parse(d).get("bulletInfo")
                data_list.append(d_dict)
            return data_list
        return

    def get_link(self, url) -> List[str]:
        _req = self._req
        res = _req.request("GET", url,
                           headers={"Accept-Encoding": "gzip,deflate,compress"}, impersonate="chrome124")
        res.encoding = "UTF-8"
        js_url = re.findall(r'<script src="(.*?)" referrerpolicy="no-referrer-when-downgrade">', res.text)[0]
        res = _req.request('GET', f'https:{js_url}', headers={'referer': url})
        tv_id = re.findall('"tvId":([0-9]+)', res.text)[0]
        base_url = f"https://cmts.iqiyi.com/bullet/{tv_id[-4:-2]}/{tv_id[-2:]}/{tv_id}_300_%s.z"
        return [base_url]

    def parse(self):
        data_list = []
        for data in tqdm(self.data_list):
            for item in data:
                try:
                    _d = self.get_data_dict()
                    _d.time = int(item.get("showTime"))
                    _d.text = item.get("content")
                    _d.color = int(item.get("color"), 16)
                    _d.style["size"] = int(item.get("font"))
                    data_list.append(_d)
                except Exception as e:
                    logger.error(e)
                    pass
        return data_list

    def main(self, links: List[str]):
        page = 1
        link = links[0]
        while True:
            # 一次获取20页的数据
            url_list = [link % i for i in range(page, page + 20)]
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(url_list))) as executor:
                fun = partial(self.request_data_by_iqiyi, "GET", headers={'Content-Type': 'application/octet-stream'})
                results = list(tqdm(executor.map(fun, url_list),
                                    total=len(url_list),
                                    desc=f"爱奇艺弹幕获取-{page}-{page + 19}"))
                self.data_list.extend([r for r in results if r is not None])
                if len([r for r in results if r is None]) > 0:
                    break
                page += 20
        return self.data_list

    def getImg(self, url):
        _req = requests.Session(impersonate="chrome124")
        res = _req.request("GET", url,
                           headers={"Accept-Encoding": "gzip,deflate,compress"}, impersonate="chrome124")
        res.encoding = "UTF-8"
        tv_id = re.findall('"tvId":([0-9]+)', res.text)[0]

        Imgurl = f'https://emoticon-sns.iqiyi.com/jaguar-core/danmu_config?qyId=36d9d90bed6d447b1b72be2cd7c8e4ba&qipuId=common&tvid={tv_id}'

        res = _req.get(Imgurl)
        emoji_data_list = []
        for item in res.json().get('data', []):
            emoji_data_list.append(
                {
                    'emoji_code': item.get('name'),
                    'emoji_url': item.get('url'),
                }
            )
        return emoji_data_list

    def get_episode_url(self, url):
        _req = requests.Session(impersonate="chrome124")
        res = _req.request("GET", url,
                           headers={"Accept-Encoding": "gzip,deflate,compress"}, impersonate="chrome124")
        res.encoding = "UTF-8"
        js_url = re.findall(r'<script src="(.*?)" referrerpolicy="no-referrer-when-downgrade">', res.text)[0]
        res = _req.request('GET', f'https:{js_url}', headers={'referer': url})
        tv_id = re.findall('"tvId":([0-9]+)', res.text)[0]
        params = f'entity_id={tv_id}&src=pca_tvg&timestamp={int(time.time())}&secret_key=howcuteitis'
        url = f'https://mesh.if.iqiyi.com/tvg/v2/lw/base_info?{params}&sign={get_md5(params).upper()}'
        res = _req.request('GET', url, headers={'referer': url})
        jsonpath_expr = parse('$..bk_title')
        matches = [match for match in jsonpath_expr.find(res.json())]
        result_objs = [match.context.value for match in matches if match.value == "选集"]
        url_dict = {}
        for result_obj in result_objs:
            d = result_obj.get('data', {}).get('data', [{}])[0].get('videos', {}).get('feature_paged', {})

            for item in d[list(d.keys())[0]]:
                if item.get('page_url'):
                    url_dict[f"{item.get('album_order')}"] = item.get('page_url')

        return url_dict


class GetDanmuMgtv(GetDanmuBase):
    name = "芒果TV"
    domain = "mgtv.com"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_video_info = "https://pcweb.api.mgtv.com/video/info"
        self.api_danmaku = "https://galaxy.bz.mgtv.com/rdbarrage"

    def get_link(self, url) -> List[str]:
        _u = url.split(".")[-2].split("/")
        cid = _u[-2]
        vid = _u[-1]
        params = {
            'cid': cid,
            'vid': vid,
        }
        res = request_data("GET", url=self.api_video_info, params=params)
        _time = res.json().get("data", {}).get("info", {}).get("time")
        end_time = self.time_to_second(_time.split(":")) * 1000

        return [f'{self.api_danmaku}?vid={vid}&cid={cid}&time={item}' for item in range(0, end_time, 60 * 1000)]

    def parse(self):
        data_list = []
        for _data in tqdm(self.data_list):
            data = _data.json()
            if data.get("data", {}).get("items", []) is None:
                continue
            for d in data.get("data", {}).get("items", []):
                _d = self.get_data_dict()
                _d.time = d.get('time', 0) / 1000
                _d.text = d.get('content', '')
                data_list.append(_d)
        return data_list

    def main(self, links: List[str]):
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(links))) as executor:
            fun = partial(self.request_data, requests, "GET")
            results = list(tqdm(executor.map(fun, links),
                                total=len(links),
                                desc="芒果TV弹幕获取"))
            self.data_list.extend(results)

        return self.data_list


class GetDanmuYouku(GetDanmuBase):
    name = "优酷"
    domain = "v.youku.com"

    def __init__(self):
        super().__init__()
        self.req = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        }
        self.get_cna()
        self.get_tk_enc()

    def get_cna(self):
        url = "https://log.mmstat.com/eg.js"
        res = self.request_data(self.req, "GET", url, headers=self.headers)

    def get_tk_enc(self):
        res = self.request_data(self.req, "GET",
                                "https://acs.youku.com/h5/mtop.com.youku.aplatform.weakget/1.0/?jsv=2.5.1&appKey=24679788",
                                headers=self.headers)
        if '_m_h5_tk' in res.cookies.keys() and '_m_h5_tk_enc' in res.cookies.keys():
            return True
        return False

    def get_vinfos_by_video_id(self, video_id):
        url = "https://openapi.youku.com/v2/videos/show.json"
        params = {
            'client_id': '53e6cc67237fc59a',
            'video_id': video_id,
            'package': 'com.huawei.hwvplayer.youku',
            'ext': 'show',
        }
        res = self.request_data(self.req, "GET", url, params=params, headers=self.headers)
        return res.json().get('duration')

    def get_msg_sign(self, msg_base64):
        secret_key = 'MkmC9SoIw6xCkSKHhJ7b5D2r51kBiREr'
        combined_msg = msg_base64 + secret_key
        hash_object = hashlib.md5(combined_msg.encode())
        return hash_object.hexdigest()

    def yk_t_sign(self, token, t, appkey, data):
        text = '&'.join([token, t, appkey, data])
        md5_hash = hashlib.md5(text.encode())
        return md5_hash.hexdigest()

    def get_link(self, url) -> List:
        if 'vid=' in url:
            # 从URL参数中提取vid
            vid_match = re.search(r'vid=([^&=]+)', url)
            if vid_match:
                # 处理可能的URL编码
                video_id = vid_match.group(1).replace('%3D', '=').replace('=', '')
                print(f"从URL参数提取vid: {video_id}")
            else:
                print("无法从URL参数中提取vid")
                return []
        else:
            # 原来的提取逻辑
            video_id = url.split('?')[0].split('/')[-1].replace("id_", '').split('.html')[0]
        max_mat = self.get_vinfos_by_video_id(video_id)
        try:
            segments = int(float(max_mat) / 60) + 1
        except:
            segments = 10  # 默认10个分段

        # 创建所有时间段的参数列表
        all_params = []
        for mat in range(segments):
            all_params.append({
                'vid': video_id,
                'mat': mat
            })
        return all_params

    def parse(self):
        data_list = []
        for data in tqdm(self.data_list):
            result = json.loads(data.get('data', {}).get('result', {}))
            if result.get('code', '-1') == '-1':
                continue
            danmus = result.get('data', {}).get('result', [])
            for danmu in danmus:
                _d = self.get_data_dict()
                _d.time = danmu.get('playat') / 1000
                _d.color = json.loads(danmu.get('propertis', '{}')).get('color', _d.color)
                _d.text = danmu.get('content')
                data_list.append(_d)
        return data_list

    def fetch_segment(self, params):
        """获取单个时间段的弹幕"""
        try:
            video_id = params.get('vid')
            mat = params.get('mat')

            url = "https://acs.youku.com/h5/mopen.youku.danmu.list/1.0/"
            msg = {
                'ctime': int(time.time() * 1000),
                'ctype': 10004,
                'cver': 'v1.0',
                'guid': self.req.cookies.get('cna'),
                'mat': mat,
                'mcount': 1,
                'pid': 0,
                'sver': '3.1.0',
                'type': 1,
                'vid': video_id
            }

            msg['msg'] = base64.b64encode(json.dumps(msg).replace(' ', '').encode('utf-8')).decode('utf-8')
            msg['sign'] = self.get_msg_sign(msg['msg'])
            t = int(time.time() * 1000)

            # 检查token是否存在
            token = self.req.cookies.get('_m_h5_tk')
            if not token:
                print("优酷token不存在，重新获取")
                self.get_tk_enc()
                token = self.req.cookies.get('_m_h5_tk')
                if not token:
                    print("无法获取优酷token")
                    return None

            params = {
                'jsv': '2.5.6',
                'appKey': '24679788',
                't': t,
                'sign': self.yk_t_sign(token[:32], str(t), '24679788',
                                       json.dumps(msg).replace(' ', '')),
                'api': 'mopen.youku.danmu.list',
                'v': '1.0',
                'type': 'originaljson',
                'dataType': 'jsonp',
                'timeout': '20000',
                'jsonpIncPrefix': 'utility'
            }

            headers = self.headers.copy()
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            headers['Referer'] = 'https://v.youku.com'

            res = self.request_data(self.req, "POST", url, data={"data": json.dumps(msg).replace(' ', '')},
                                    headers=headers, params=params)

            if res and hasattr(res, 'json'):
                return res.json()
            return None
        except Exception as e:
            print(f"获取优酷弹幕分段失败（mat={mat}）: {e}")
            return None

    def main(self, all_params):

        # 使用线程池并行获取所有时间段的弹幕
        self.data_list = []
        if all_params:
            print(f"优酷: 开始并行获取 {len(all_params)} 个时间段的弹幕")
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(all_params))) as executor:
                results = list(tqdm(executor.map(self.fetch_segment, all_params),
                                    total=len(all_params),
                                    desc="优酷弹幕获取"))
                # 过滤掉失败的结果
                valid_results = [r for r in results if r is not None]
                self.data_list.extend(valid_results)

        # 如果没有获取到任何数据，回退到传统方法
        if not self.data_list:
            print("优酷多线程获取失败，回退到单线程模式")
            for item in range(all_params):
                try:
                    result = self.fetch_segment({
                        'vid': item.get('vid'),
                        'mat': item.get('mat')
                    })
                    if result:
                        self.data_list.append(result)
                except Exception as e:
                    print(f"单线程获取优酷弹幕失败（mat={item.get('mat')}）: {e}")

        return self.data_list

    def getImg(self, url):
        api_url = 'https://acs.youku.com/h5/mtop.youku.danmu.common.profile/1.0'
        video_id = url.split('?')[0].split('/')[-1].replace("id_", '').split('.html')[0]
        msg = {
            'pid': 0,
            'ctype': 10004,
            'sver': '3.1.0',
            'cver': 'v1.0',
            'ctime': int(time.time() * 1000),
            'guid': self.req.cookies.get('cna'),
            'vid': video_id
        }
        msg['msg'] = base64.b64encode(json.dumps(msg).replace(' ', '').encode('utf-8')).decode('utf-8')
        msg['sign'] = self.get_msg_sign(msg['msg'])
        t = int(time.time() * 1000)
        params = {
            'jsv': '2.5.6',
            'appKey': '24679788',
            't': t,
            'sign': self.yk_t_sign(self.req.cookies.get('_m_h5_tk')[:32], str(t), '24679788',
                                   json.dumps(msg).replace(' ', '')),
            'api': 'mopen.youku.danmu.list',
            'v': '1.0',
            'type': 'originaljson',
            'dataType': 'jsonp',
            'timeout': '20000',
            'jsonpIncPrefix': 'utility'
        }
        headers = self.headers.copy()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        headers['Referer'] = 'https://v.youku.com'
        res = self.request_data(self.req, "POST", api_url, data={"data": json.dumps(msg).replace(' ', '')},
                                headers=headers,
                                params=params)
        emoji_infos = res.json().get('data', {}).get('data', {}).get('danmuEmojiEnter', {}).get('danmuDynamicEmojiVO',
                                                                                                [])
        emoji_data_list = []
        for emoji_info in emoji_infos:
            emoji_data_list.append(
                {
                    'emoji_code': emoji_info.get('subtext'),
                    'emoji_url': emoji_info.get('previewPic'),
                }
            )
        return emoji_data_list


class GetDanmuSoHu(GetDanmuBase):
    name = "搜狐"
    domain = "tv.sohu.com"

    def __init__(self):
        super().__init__()
        self.req = requests.Session(impersonate="chrome124")

    def get_link(self, url) -> List:
        res = self.req.get(url)
        vid = re.findall('vid="(.*?)";', res.text)[0]
        aid = re.findall('playlistId="(.*?)";', res.text)[0]
        base_url = f'https://api.danmu.tv.sohu.com/dmh5/dmListAll?act=dmlist_v2&request_from=h5_js&vid={vid}&aid={aid}&time_begin=%s&time_end=%s'
        return [base_url]

    def parse(self):
        data_list = []
        for _data in tqdm(self.data_list):
            data = _data.json()
            for d in data.get("info", {}).get("comments", []):
                _d = self.get_data_dict()
                _d.time = d.get('v', 0)
                _d.text = d.get('c', '')
                data_list.append(_d)
        return data_list

    def main(self, links):
        self.data_list = []
        page = 0
        link = links[0]
        while True:
            url_list = [link % (i * 300, (i + 1) * 300) for i in range(page, page + 20)]
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(url_list))) as executor:
                fun = partial(self.request_data, self.req, "GET")
                results = list(tqdm(executor.map(fun, url_list),
                                    total=len(url_list),
                                    desc="搜狐弹幕获取"))
                # 过滤掉失败和空结果
                valid_results = [r for r in results if 'comments' in r.text]
                self.data_list.extend(valid_results)
                if len([r for r in results if 'comments' not in r.text]) > 0:
                    break
                page += 20

        # 如果没有获取到任何数据，回退到传统方法
        if not self.data_list:
            print("多线程获取失败，回退到单线程模式")
            page = 0
            while True:
                _res = self.req.get(link % (page * 300, (page + 1) * 300))
                if 'comments' not in _res.text:
                    break
                page += 1
                self.data_list.append(_res.json())

        return self.data_list

    def get_episode_url(self, url):
        _res = self.req.get(url)
        vid = re.findall('vid="(.*?)";', _res.text)[0]
        play_list_id = re.findall('playlistId="(.*?)";', _res.text)[0]
        params = {
            "playlistid": play_list_id,
            "vid": vid
        }
        res = self.req.get("https://pl.hd.sohu.com/videolist", params)
        res.encoding = res.charset_encoding
        res_data = json.loads(res.text.encode("utf-8"))
        url_dict = {}
        for item in res_data.get('videos', []):
            url_dict[item.get('order')] = item.get('pageUrl')
        return url_dict


def download_barrage(_url):
    # while True:
    for c in GetDanmuBase.__subclasses__():
        if c.domain in _url:
            d = c().get(_url)
            if d:
                return d


if __name__ == '__main__':
    print(GetDanmuBase.__subclasses__())
    danmu = GetDanmuSoHu()
    a = danmu.get(
        "https://tv.sohu.com/v/MjAyNTA0MTEvbjYyMDA2MjgxOC5zaHRtbA==.html",
    )
    print()
