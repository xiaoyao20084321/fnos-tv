import requests
from flask import Blueprint, request

from Config import fnos_url
from core.db.base import CRUDBase
from core.db.model.recordDb import RecordDb

fnos = Blueprint('fnos', __name__, url_prefix='/fnos')


@fnos.post('/v/api/v1/play/record')
def record():
    """
    记录播放记录，推算跳过片段
    :return: 
    """
    data = request.json
    # 转发到飞牛原始接口
    res = requests.post(f"{fnos_url}/v/api/v1/play/record", json=data, headers={
        "Cookie": request.headers.get('Cookie'),
        "authorization": request.headers.get('authorization'),
        "authx": request.headers.get('authx'),
    })
    record_db = CRUDBase(RecordDb)
    record_db.add(
        guid=data.get("guid"),
        episode_guid=data.get("item_guid"),
        time=data.get("ts"),
        create_time=data.get("create_time"),
        playback_speed=data.get("playback_speed"),
    )
    return res.json()
    # return 'ok'
