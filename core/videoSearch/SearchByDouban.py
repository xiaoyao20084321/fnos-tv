import re
from typing import List, Dict
from urllib import parse
from urllib.parse import urlparse

import cn2an

from Fuction import request_data, resolve_url_query
from core.videoSearch.Base import VideoSearchBase





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


class DoubanSearch(VideoSearchBase):
    def __init__(self, ):
        super().__init__()

    @staticmethod
    def douban_select(name: str, tv_num: str, season: bool):
        url = "https://frodo.douban.com/api/v2/search/weixin"

        params = {
            'q': name,
            'start': "0",
            'count': "20",
            'apiKey': "0ac44ae016490db2204ce0a042db2916"
        }

        headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090c33)XWEB/11581",
            'xweb_xhr': "1",
            'content-type': "application/json",
            'sec-fetch-site': "cross-site",
            'sec-fetch-mode': "cors",
            'sec-fetch-dest': "empty",
            'referer': "https://servicewechat.com/wx2f9b06c1de1ccfca/99/page-frame.html",
            'accept-language': "zh-CN,zh;q=0.9"
        }
        res = request_data("GET", url, params=params, headers=headers)
        json_data = res.json().get('items', [])

        for i in json_data:
            data = i.get('target', {})
            # 只获取有播放链接的
            if i.get('layout') != 'subject' or not data.get('has_linewatch'):
                continue
            d_tv_num = re.findall("第(.*?)季", data.get('title', ""))
            if not d_tv_num:
                d_tv_num = re.findall(rf'{name}(\d+)', data.get('title', ""))
            if not d_tv_num:
                roman_num = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"]
                roman_num_str = '|'.join(roman_num)
                _d_tv_num = re.findall(f'{name}([{roman_num_str}]+)', data.get('title', ""))
                if _d_tv_num:
                    d_tv_num = [roman_num.index(_d_tv_num[0])]
            if not d_tv_num:
                d_tv_num = "一"
            else:
                d_tv_num = d_tv_num[0]
            try:
                d_tv_num = cn2an.an2cn(int(d_tv_num))

            except:
                pass
            if name.split(" ")[0] in data.get('title', "") and (tv_num == name or d_tv_num == tv_num):
                return i

    @staticmethod
    def douban_get_first_url(target_id):
        url = f'https://frodo.douban.com/api/v2/tv/{target_id}?apiKey=0ac44ae016490db2204ce0a042db2916'
        headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090c33)XWEB/11581",
            'xweb_xhr': "1",
            'content-type': "application/json",
            'sec-fetch-site': "cross-site",
            'sec-fetch-mode': "cors",
            'sec-fetch-dest': "empty",
            'referer': "https://servicewechat.com/wx2f9b06c1de1ccfca/99/page-frame.html",
            'accept-language': "zh-CN,zh;q=0.9"
        }
        res = request_data("GET", url, headers=headers)
        json_data = res.json().get('vendors', [])
        url_list = []
        for item in json_data:
            if item.get('url') and 'douban' not in item.get('url').split('?')[0]:
                url_list.append(item.get('url'))
                continue
            if item.get('uri'):
                url_list.append(item.get('uri'))
        return url_list

    def main(self, name: str, tv_num: str, season) -> List[str] | None:
        douban_data = self.douban_select(name, tv_num, season)
        if not douban_data:
            return None
        douban_id = douban_data['target_id']
        platform_url_list = other2http(self.douban_get_first_url(douban_id))
        if not platform_url_list:
            return None
        return platform_url_list
