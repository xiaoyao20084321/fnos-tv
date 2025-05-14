import concurrent.futures
from functools import partial
from typing import List

from curl_cffi import requests
from tqdm import tqdm

from Fuction import request_data
from core.danmu.base import GetDanmuBase


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
