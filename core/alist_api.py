# -*- coding: UTF-8 -*-
import json
import os
from urllib import parse

import requests
from retrying import retry
import requests as req

# from Fuctions.Fuction import request_data
alist_host = None
alist_token = None


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


def login(user_name, password):
    url = f"{alist_host}/api/auth/login"
    data = {
        "username": user_name,
        "password": password,
        "otp_code": ""
    }
    res = request_data("POST", url, json=data, )
    return res


# 搜索文件
def search(file_name, page: int = 1, per_page: int = 100):
    url = f'{alist_host}/api/fs/search'
    header = {"Authorization": alist_token, }
    body = {"parent": "/",
            "keywords": file_name,
            "page": page,
            "per_page": per_page
            }

    return request_data("post", url, json=body, headers=header, timeout=30)


# 获取下载信息
def fs_get(path):
    url = f'{alist_host}/api/fs/get'
    header = {"Authorization": alist_token,
              'Cache-Control': 'no-cache'
              }
    body = {"path": path}
    return request_data("post", url, json=body, headers=header, timeout=30)


# 查询指定存储信息
def storage_get(storage_id):
    url = f'{alist_host}/api/admin/storage/get?id={str(storage_id)}'
    header = {"Authorization": alist_token}

    return request_data("get", url, headers=header, timeout=30)


# 新建存储
def storage_create(body):
    url = f'{alist_host}/api/admin/storage/create'
    header = {'Authorization': alist_token}

    return request_data("post", url, json=body, headers=header, timeout=30)


# 更新存储
def storage_update(body):
    url = f'{alist_host}/api/admin/storage/update'
    header = {"Authorization": alist_token}

    return request_data("post", url, json=body, headers=header, timeout=30)


# 获取存储列表
def storage_list():
    url = f'{alist_host}/api/admin/storage/list'
    header = {"Authorization": alist_token, }

    return request_data("get", url, headers=header, timeout=30)


# 删除指定存储
def storage_delete(storage_id):
    url = f'{alist_host}/api/admin/storage/delete?id={str(storage_id)}'
    header = {"Authorization": alist_token}

    return request_data("post", url, headers=header, timeout=30)


# 开启存储
def storage_enable(storage_id):
    url = f'{alist_host}/api/admin/storage/enable?id={str(storage_id)}'
    header = {"Authorization": alist_token}

    return request_data("post", url, headers=header, timeout=30)


# 关闭存储
def storage_disable(storage_id):
    url = f'{alist_host}/api/admin/storage/disable?id={str(storage_id)}'
    header = {"Authorization": alist_token}

    return request_data("post", url, headers=header, timeout=30)


# 上传文件
# from https://github.com/lym12321/Alist-SDK/blob/dde4bcc74893f9e62281482a2395abe9a1dd8d15/alist.py#L67

def upload(local_path, remote_path, file_name):
    useragent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
    url = f'{alist_host}/api/fs/put'
    header = {
        'UserAgent': useragent,
        'Authorization': alist_token,
        'File-Path': parse.quote(f'{remote_path}/{file_name}'),
        'Content-Length': f'{os.path.getsize(local_path)}'
    }

    return json.loads(
        request_data("put", url, headers=header, data=open(local_path, 'rb').read()).text)


# 获取列表，强制刷新列表

def refresh_list(path, per_page: int = 0):
    url = f'{alist_host}/api/fs/list'
    header = {"Authorization": alist_token}
    body = {"path": path, "page": 1, "per_page": per_page, "refresh": True}

    return request_data("post", url, json=body, headers=header, timeout=30)


def delete_file(path: str, names: list):
    url = f'{alist_host}/api/fs/remove'
    header = {"Authorization": alist_token}
    data = {
        'dir': path,
        'names': names
    }
    return request_data("post", url, headers=header, json=data)


def driver_info(driver):
    url = f'{alist_host}/api/admin/driver/info?driver={driver}'
    header = {"Authorization": alist_token}
    return request_data('GET', url=url, headers=header)


# 获取驱动列表

def get_driver():
    url = f'{alist_host}/api/admin/driver/list'
    header = {"Authorization": alist_token}

    return request_data("get", url, headers=header, timeout=30)


def alist_mkdir(path):
    url = f'{alist_host}/api/fs/mkdir'
    header = {"Authorization": alist_token}
    data = {
        "path": path
    }
    return request_data("POST", url, headers=header, json=data)


def put_file(data, path):
    url = f'{alist_host}/api/fs/put'
    header = {"Authorization": alist_token,
              'File-Path': parse.quote(path),
              }
    files = {'files': (os.path.split(path)[-1], data)}
    return request_data("PUT", url, headers=header, data=data)


def rename_file(path, name):
    url = f'{alist_host}/api/fs/rename'
    header = {"Authorization": alist_token}
    data = {
        "name": name,
        "path": path
    }

    return request_data("post", url, headers=header, json=data)


def get_link(_path):
    url = f'{alist_host}/api/fs/link'
    header = {"Authorization": alist_token}
    data = {
        "path": _path
    }
    return request_data("POST", url, headers=header, json=data)


def copy(src_dir, dst_dir, name):
    url = f'{alist_host}/api/fs/copy'
    header = {"Authorization": alist_token}
    data = {
        "src_dir": src_dir,
        "dst_dir": dst_dir,
        "names": [
            name
        ]
    }
    return request_data("POST", url, headers=header, json=data)


def undone():
    url = f'{alist_host}/api/admin/task/copy/undone'
    header = {"Authorization": alist_token}
    return request_data("gET", url, headers=header)


# print(json.dumps(json.loads(get_driver().text)['data']))

if __name__ == '__main__':
    a = fs_get('/本地/抖音上传temp/node-v18.17.0-x64.msi')
    print()
