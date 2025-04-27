import hashlib
import os
import re
import sys
import zipfile
from datetime import datetime
from itertools import combinations
from urllib import parse

import cn2an
import requests as req
from curl_cffi import requests
from retrying import retry


@retry(stop_max_attempt_number=5, wait_random_min=1000, wait_random_max=2000)
def request_data(method, url, status_code=None, **kwargs):
    """
    发送请求
    :param method: 请求方式
    :param url: 请求URL
    :param status_code: 成功的状态码
    :param kwargs:
    :return:
    """
    if 'timeout' not in kwargs.keys():
        kwargs['timeout'] = 15
    if 'impersonate' in kwargs.keys():
        res = requests.request(method, url, **kwargs)
    else:
        res = req.request(method, url, **kwargs)
    # res.encoding = res.apparent_encoding
    if status_code:
        if res.status_code == status_code:
            return res
        else:
            return
    return res


def get_platform_link(douban_id):
    res = request_data("GET", f'https://movie.douban.com/subject/{douban_id}/', headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    urls = re.findall('https://www.douban.com/link2/\?url=(.*?)",.+ep:.+"(.*?)"', res.text)
    url_dict = {}
    for url in urls:
        if url[1] in url_dict.keys():
            url_dict[url[1]].append(parse.unquote(url[0]))
        else:
            url_dict[url[1]] = [parse.unquote(url[0])]

    return url_dict


def douban_select(name: str, tv_num: str, season: bool):
    if tv_num is None:
        tv_num = "一"
    else:
        try:
            tv_num = cn2an.an2cn(int(tv_num))
        except (ValueError, TypeError):
            # 如果转换失败，保持原样
            pass
    
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
            d_tv_num = re.findall(f'{name}(\d+)', data.get('title', ""))
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
        if item.get('url'):
            url_list.append(item.get('url'))
    return url_list


def get_md5(str):
    md5 = hashlib.md5()
    md5.update(str.encode('utf-8'))
    return md5.hexdigest()


def fetch_latest_dist_zip(repo, asset_name='dist.zip'):
    """
    拉取指定 GitHub 仓库最新发布版中命名为 dist.zip 的下载链接，并下载该文件。

    参数:
      repo: 字符串，仓库地址，格式为 "用户名/仓库名"
      asset_name: 要查找的资产名称，默认为 "dist.zip"

    返回:
      下载的文件路径，如果下载失败则退出程序。
    """
    # GitHub API URL，用于获取最新发布信息
    api_url = f"https://api.github.com/repos/{repo}/releases/latest"
    response = requests.get(api_url, headers={"User-Agent": "Awesome-Octocat-App"})
    if response.status_code != 200:
        print(f"获取发布信息失败，状态码：{response.status_code}", file=sys.stderr)
        sys.exit(1)

    release_info = response.json()
    assets = release_info.get("assets", [])
    download_url = None

    # 遍历发布中的所有资产，查找名称为 asset_name 的文件
    for asset in assets:
        if asset.get("name") == asset_name:
            download_url = asset.get("browser_download_url")
            break

    if not download_url:
        print(f"未找到名为 {asset_name} 的资产", file=sys.stderr)
        return

    print(f"找到 {asset_name} 的下载链接：{download_url}")

    # 下载该文件
    download_response = requests.get(download_url, stream=True, headers={"User-Agent": "Awesome-Octocat-App"})
    if download_response.status_code != 200:
        print(f"下载文件失败，状态码：{download_response.status_code}", file=sys.stderr)
        return

    file_path = asset_name
    with open(file_path, "wb") as f:
        for chunk in download_response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    print(f"成功下载到 {file_path}")
    return file_path


def unzip_file(zip_path, extract_dir=None):
    """
    解压指定的 zip 文件到目标目录

    参数:
      zip_path: zip 文件路径
      extract_dir: 目标目录，若为 None 则解压到 zip 文件所在目录

    返回:
      解压后的文件列表
    """
    if extract_dir is None:
        extract_dir = os.path.dirname(zip_path)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # 解压所有文件
        zip_ref.extractall(extract_dir)
        # 返回所有解压出来的文件名列表
        return zip_ref.namelist()


def find_skipped_segments(records):
    """
    寻找跳过的片段
    :param records: 
    :return: 
    """
    skipped_segments = []

    # 先按 create_time 排序
    records.sort(key=lambda x: x['create_time'])

    base_data = [dict(**records[0])]
    base_data[0]['time'] = 0
    records = base_data + records

    for i in range(len(records) - 1):
        cur = records[i]
        nxt = records[i + 1]

        # 拆变量
        t1 = cur['time']
        t2 = nxt['time']
        ts1 = cur['create_time']
        ts2 = nxt['create_time']
        speed = float(cur.get('playback_speed', 1.0))

        # 时间间隔
        dt_real = ts2 - ts1
        dt_expected = dt_real * speed
        dt_video = t2 - t1
        skipped = max(0, dt_video - dt_expected)

        if skipped > 3:
            skipped_segments.append({
                'id': cur['id'],
                'guid': cur['guid'],
                'episode_guid': cur['episode_guid'],
                'create_time': cur['create_time'],
                'skipped_start': t1,
                'skipped_end': t2,
                'skipped': round(skipped, 2),
                'speed': speed,
                'real_interval': dt_real,
                'video_jump': dt_video
            })

    return skipped_segments


def calculate_repeat_rate(data, tolerance=15, threshold=0.6):
    """
    寻找多集跳过片段中重合率大于70%的，这样才能确定没有判断错误
    :param data: 
    :param tolerance: 
    :param threshold: 
    :return: 
    """
    results = []
    for key1, key2 in combinations(data.keys(), 2):
        segs1 = data[key1]
        segs2 = data[key2]
        repeat_count = 0

        matched2 = set()  # 避免 segs2 中一个段被重复匹配
        ret_data = []

        for seg1 in segs1:
            for idx2, seg2 in enumerate(segs2):
                if idx2 in matched2:
                    continue
                if abs(seg1['skipped_start'] - seg2['skipped_start']) <= tolerance and \
                        abs(seg1['skipped_end'] - seg2['skipped_end']) <= tolerance:
                    repeat_count += 1
                    matched2.add(idx2)
                    ret_data.append(seg2)
                    break

        total_segments = len(segs1) + len(segs2)
        repeat_rate = (2 * repeat_count) / total_segments if total_segments > 0 else 0
        if repeat_rate >= threshold:
            results.append({
                'episode_pair': (key1, key2),
                'repeat_count': repeat_count,
                'total_segments': total_segments,
                'repeat_rate': repeat_rate,
                'data': ret_data
            })
    return results


def merge_skipped_segments(segments):
    """
    去除重复的区间
    :param segments: 
    :return: 
    """
    # 先按 skipped_start 排序
    segments = sorted(segments, key=lambda x: x['skipped_start'])

    merged = []
    for seg in segments:
        if not merged:
            merged.append(seg)
        else:
            last = merged[-1]
            # 判断是否有重叠
            if seg['skipped_start'] <= last['skipped_end']:
                # 有重叠，保留更大的段（区间更大）
                len_last = last['skipped_end'] - last['skipped_start']
                len_cur = seg['skipped_end'] - seg['skipped_start']
                if len_cur < len_last:
                    merged[-1] = seg  # 替换为更短的那个
            else:
                merged.append(seg)
    return merged
