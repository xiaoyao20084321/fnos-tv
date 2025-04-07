import re
from urllib import parse

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
