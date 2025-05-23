import json
import threading
import time

from func_timeout import FunctionTimedOut, func_timeout
import websocket
from loguru import logger

from Config import fnos_url
from core.Fnos.GetFnOsData import GetFnOsData


class FnOsWsBase:
    def __init__(self, type='main'):
        self.ws = ws = websocket.WebSocketApp(
            f'wss://{fnos_url.split('//')[1]}/websocket?type={type}',
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.isRun = False
        self.pending_futures = {}

    def on_message(self, ws, message):
        logger.info(f"接收到消息：{message}")
        message = json.loads(message)
        req_id = message.get('reqid', None)
        if req_id is not None and req_id in self.pending_futures:
            self.pending_futures[req_id] = message

    def on_error(self, ws, error):
        logger.error(f"错误：{error}")

    def on_close(self, ws, close_status_code, close_msg):
        logger.error("连接关闭")

    def on_open(self, ws):
        # def run():
        #     for i in range(3):
        #         msg = f"sync hello {i}"
        #         print(f"发送：{msg}")
        #         ws.send(msg)
        #     ws.close()
        # 
        # run()
        self.isRun = True
        logger.info("WS链接已建立")

    def get_msg(self, req_id):
        while True:
            ret_data = self.pending_futures.get(req_id, None)
            if ret_data is not None:
                self.pending_futures.pop(req_id, None)
                return ret_data

    def sleep_open(self):
        while True:
            if self.isRun:
                return

    def send(self, msg, req_id, time_out=10):
        try:
            # 判断msg的类型是否为字典
            if type(msg) != str:
                msg = json.dumps(msg)
            func_timeout(5, self.sleep_open)
            self.pending_futures[req_id] = None
            self.ws.send(msg)
            return func_timeout(time_out, self.get_msg, args=(req_id,))
        except FunctionTimedOut:
            logger.error("获取返回值超时")
        except Exception as e:
            logger.error(e)

    def send_heartbeat(self):
        while True:
            if self.ws and self.ws.sock and self.ws.sock.connected:
                heartbeat_msg = {
                    "req": "ping"
                }
                try:
                    self.ws.send(json.dumps(heartbeat_msg))
                    logger.debug("发送心跳包")
                except Exception as e:
                    logger.warning(f"发送心跳失败：{e}")
            time.sleep(10)

    def start(self):
        threading.Thread(target=self.ws.run_forever, daemon=True).start()
        threading.Thread(target=self.send_heartbeat, daemon=True).start()


class FnOsWsFile(FnOsWsBase):
    def __init__(self, fn_os: GetFnOsData):
        """
        :param fn_os: 有登录信息的实例化类
        """
        super().__init__('file')
        self.fn_os = fn_os

    def login(self):
        si_msg = self.fn_os.get_si()
        si_ret = self.send(**si_msg)
        auth_token = self.fn_os.auth_token(si_ret.get('si'))
        self.send(**auth_token)
