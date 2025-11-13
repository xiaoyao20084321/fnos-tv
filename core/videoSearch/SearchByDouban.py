import re
from typing import List, Dict
from urllib import parse
from urllib.parse import urlparse

import cn2an

from Fuction import request_data, resolve_url_query
from core.videoSearch.Base import VideoSearchBase
from core.videoSearch.videoSearchType import VideoDataDto


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
    def douban_select(name: str):
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
        id_list = []

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
            id_list.append(i.get('target_id'))
        return id_list

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
        res_json = res.json()
        json_data = res_json.get('vendors', [])
        url_list = []
        title = res_json.get('title', '')
        d_tv_num = re.findall("第(.*?)季", title)
        if not d_tv_num:
            roman_num = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"]
            roman_num_str = '|'.join(roman_num)
            _d_tv_num = re.findall(f'{re.escape(title)}([{roman_num_str}]+)', title)
            if _d_tv_num:
                d_tv_num = [roman_num.index(_d_tv_num[0])]
        if not d_tv_num:
            d_tv_num = re.findall(rf'(\d+)', title)
        if not d_tv_num:
            d_tv_num = "一"
        else:
            d_tv_num = d_tv_num[0]
        try:
            d_tv_num = cn2an.an2cn(int(d_tv_num))

        except:
            pass
        episodes_count = res_json.get('episodes_count', 0)
        img_url = res_json.get('pic', {}).get('large', '')
        if len(json_data) == 0:
            return None
        for item in json_data:
            if item.get('url') and 'douban' not in item.get('url').split('?')[0]:
                url_list += other2http([item.get('url')])
                continue
            if item.get('uri'):
                url_list += other2http([item.get('uri')])

        return VideoDataDto(
            title=title,
            season_number=cn2an.cn2an(d_tv_num),
            source="douban",
            url=url_list,
            img_url=img_url,
            episodeCount=episodes_count
        )

    def main(self, name: str) -> List[VideoDataDto]:
        douban_id_list = self.douban_select(name)
        if not douban_id_list:
            return []
        video_list = []
        for douban_id in douban_id_list:
            video_data = self.douban_get_first_url(douban_id)
            if video_data:
                video_list.append(video_data)
        return video_list


if __name__ == '__main__':
    DoubanSearch().get("爱情公寓")
