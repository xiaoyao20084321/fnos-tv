import base64
import concurrent.futures
import hashlib
import json
import re
import time
from typing import List

from curl_cffi import requests
from tqdm import tqdm

from core.danmu.base import GetDanmuBase


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
