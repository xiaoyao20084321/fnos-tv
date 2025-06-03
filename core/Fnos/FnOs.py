import asyncio
import json

from core.Fnos.GetFnOsData import GetFnOsData
from core.Fnos.ws import FnOsWsBase

fn_os = GetFnOsData()
fn_os_ws = FnOsWsBase()


def if_login(func):
    def wrapper(*args, **kwargs):
        if fn_os.token is None:
            raise "未登录"
        return func(*args, **kwargs)

    return wrapper


def get_rsa_pub():
    msg = fn_os.get_rea_pub()
    future = fn_os_ws.send(**msg)
    return future


def login(username, password):
    rsa_pub = get_rsa_pub()
    assert rsa_pub, "获取res pub失败"
    msg = fn_os.login_data(username, password, rsa_pub.get('si'), rsa_pub.get('pub'))
    future = fn_os_ws.send(**msg)
    fn_os.set_login_data(**future)
    fn_os_ws.fn_os = fn_os
    return future


@if_login
def get_file_list(path: str = None):
    ls_msg = fn_os.ls(path)
    future = fn_os_ws.send(**ls_msg)
    return future


@if_login
def mountmgr_list():
    msg = fn_os.mountmgr_list()
    future = fn_os_ws.send(**msg)
    return future

