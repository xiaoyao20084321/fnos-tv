import concurrent.futures
import json
import re
from functools import partial
from typing import List

from curl_cffi import requests
from tqdm import tqdm

from core.danmu.base import GetDanmuBase


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

    def parse(self, _data):
        data_list = []
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
