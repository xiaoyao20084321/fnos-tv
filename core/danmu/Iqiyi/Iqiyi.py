import concurrent.futures
import concurrent.futures
import re
import time
from functools import partial
from typing import List
from urllib import parse
from venv import logger

import brotlicffi as brotli
from curl_cffi import requests
from jsonpath_ng import parse
from tqdm import tqdm

import core.danmu.Iqiyi.Iqiyidm_pb2 as Iqiyidm_pb2
from Fuction import get_md5, resolve_url_query
from core.danmu.base import GetDanmuBase


class GetDanmuIqiyi(GetDanmuBase):
    name = "爱奇艺"
    domain = "iqiyi.com"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._req = requests.Session(impersonate="chrome124")

    def request_data_by_iqiyi(self, method, url, *args, **kwargs):
        res = self.request_data(self._req, method, url=url, *args, **kwargs)
        if res.status_code == 200:
            return res
        return

    def get_link(self, url) -> List[str]:
        url_list = []
        _req = self._req
        res = _req.request("GET", url,
                           headers={"Accept-Encoding": "gzip,deflate,compress"}, impersonate="chrome124")
        res.encoding = "UTF-8"
        js_url = re.findall(r'<script src="(.*?)" referrerpolicy="no-referrer-when-downgrade">', res.text)[0]
        res = _req.request('GET', f'https:{js_url}', headers={'referer': url})
        tv_id = re.findall('"tvId":([0-9]+)', res.text)[0]
        video_duration = int(re.findall('"videoDuration":([0-9]+)', res.text)[0])
        step_length = 60
        max_index = int(video_duration / step_length) + 1
        for index in range(1, max_index + 1):
            i = f'{tv_id}_{step_length}_{index}cbzuw1259a'
            s = get_md5(i)[-8:]
            o = f'{tv_id}_{step_length}_{index}_{s}.br'
            url_list.append(f"https://cmts.iqiyi.com/bullet/{tv_id[-4:-2]}/{tv_id[-2:]}/{o}")
        return url_list

    def parse(self):
        data_list = []
        for data in tqdm(self.data_list):
            out = brotli.decompress(data.content)
            danmu = Iqiyidm_pb2.Danmu()
            danmu.ParseFromString(out)
            for entry in danmu.entry:
                for item in entry.bulletInfo:
                    try:
                        _d = self.get_data_dict()
                        _d.time = int(item.showTime)
                        _d.text = item.content
                        _d.color = int(item.a8, 16)
                        _d.style["size"] = int(25)
                        data_list.append(_d)
                    except Exception as e:
                        logger.error(e)
                        pass
        return data_list

    def main(self, links: List[str]):
        page = 1
        url_list = links
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(url_list))) as executor:
            fun = partial(self.request_data_by_iqiyi, "GET")
            results = list(tqdm(executor.map(fun, url_list),
                                total=len(url_list),
                                desc=f"爱奇艺弹幕获取-{page}-{page + 19}"))
            self.data_list.extend([r for r in results if r is not None])
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
        query = resolve_url_query(url)
        _req = self._req
        if query.get('tvid'):
            tv_id = query.get('tvid')[0]
        else:
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
            d = result_obj.get('data', {}).get('data', [{}])[0].get('videos', {})
            if isinstance(d, str):
                _res = _req.get(d)
                d = _res.json().get("data", {}).get('videos', {})
            d = d.get('feature_paged', {})
            for k in list(d.keys()):
                for item in d[k]:
                    if item.get('page_url'):
                        url_dict[f"{item.get('album_order')}"] = item.get('page_url')

        return url_dict
