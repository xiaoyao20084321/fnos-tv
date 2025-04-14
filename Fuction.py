import os
import re
import sys
import zipfile
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
