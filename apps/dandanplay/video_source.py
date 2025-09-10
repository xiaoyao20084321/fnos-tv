"""
视频源抽象层
支持360影视和自定义API两种数据源
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
import requests
import json

from Fuction import request_data


class VideoSourceBase(ABC):
    """视频源基础抽象类"""
    
    @abstractmethod
    def search_anime(self, keyword: str) -> Dict[str, Any]:
        """搜索动漫/影视资源"""
        pass
    
    @abstractmethod
    def get_bangumi_detail(self, bangumi_id: str, search_id: str = None, result_index: int = None) -> Dict[str, Any]:
        """获取番剧详情和剧集列表"""
        pass


class Video360Source(VideoSourceBase):
    """360影视数据源"""
    
    def search_anime(self, keyword: str) -> Dict[str, Any]:
        """调用360搜索API"""
        url = f"https://api.so.360kan.com/index?kw={keyword}&from&pageno=1&v_ap=1&tab=all"
        try:
            response = request_data("GET", url, impersonate='chrome124')
            return response.json()
        except Exception as e:
            print(f"360搜索API调用失败: {e}")
            return None
    
    def get_bangumi_detail(self, bangumi_id: str, search_id: str = None, result_index: int = None) -> Dict[str, Any]:
        """360影视通过缓存获取详情，这里返回None让调用方从缓存获取"""
        return None


class VideoApiSource(VideoSourceBase):
    """自定义API数据源"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
    
    def search_anime(self, keyword: str) -> Dict[str, Any]:
        """调用自定义搜索API"""
        url = f"{self.base_url}/api/control/search"
        params = {
            'keyword': keyword,
            'api_key': self.api_key
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"自定义API搜索调用失败: {e}")
            return None
    
    def get_bangumi_detail(self, bangumi_id: str, search_id: str = None, result_index: int = None) -> Dict[str, Any]:
        """调用自定义剧集API"""
        if not search_id or result_index is None:
            return None
            
        url = f"{self.base_url}/api/control/episodes"
        params = {
            'searchId': search_id,
            'result_index': result_index,
            'api_key': self.api_key
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"自定义API剧集调用失败: {e}")
            return None


class VideoSourceFactory:
    """视频源工厂类"""
    
    @staticmethod
    def create_source(source_type: str, api_base_url: str = None, api_key: str = None) -> VideoSourceBase:
        """根据配置创建对应的视频源"""
        if source_type == "misaka-danmu-server" and api_base_url and api_key:
            return VideoApiSource(api_base_url, api_key)
        else:
            # 默认使用360源
            return Video360Source()
