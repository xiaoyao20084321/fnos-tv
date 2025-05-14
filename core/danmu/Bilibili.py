import concurrent.futures
import re
from functools import partial
from typing import List
from venv import logger

from curl_cffi import requests
from tqdm import tqdm

from Fuction import request_data
from core.danmu.base import GetDanmuBase


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
