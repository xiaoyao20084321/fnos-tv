import concurrent.futures
import concurrent.futures
import re
import time
import zlib
from functools import partial
from typing import List
from urllib import parse
from venv import logger

import xmltodict
from curl_cffi import requests
from jsonpath_ng import parse
from tqdm import tqdm

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
        query = resolve_url_query(url)
        if query.get('tvid'):
            tv_id = query.get('tvid')[0]
        else:
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
            d = result_obj.get('data', {}).get('data', [{}])[0].get('videos', {}).get('feature_paged', {})
            for k in list(d.keys()):
                for item in d[k]:
                    if item.get('page_url'):
                        url_dict[f"{item.get('album_order')}"] = item.get('page_url')

        return url_dict
