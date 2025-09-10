"""
数据转换器
将不同数据源的格式转换为统一的内部格式
"""

from typing import Dict, List, Any


class DataConverter:
    """数据格式转换器"""
    
    @staticmethod
    def convert_360_search_result(search_data: Dict[str, Any]) -> Dict[str, Any]:
        """转换360搜索结果为DanDanPlay格式"""
        if not search_data or 'data' not in search_data:
            return {"animes": [], "errorCode": 0, "success": True, "errorMessage": ""}
        
        animes = []
        rows = search_data.get('data', {}).get('longData', {}).get('rows', [])
        
        for item in rows:
            # 搜索阶段：使用简单的集数估算，不调用复杂的get_episode_url
            episode_count = 1  # 默认1集
            
            # 优先从coverInfo获取集数信息（快速且可靠）
            if item.get('coverInfo', {}).get('txt'):
                cover_text = item.get('coverInfo', {}).get('txt', '')
                if '集' in cover_text:
                    try:
                        episode_count = int(cover_text.replace('全', '').replace('更新至', '').replace('集', ''))
                    except:
                        episode_count = 1
            # 如果coverInfo没有信息，对于电视剧类型给一个合理的估算
            elif item.get('cat_id') == '2':  # 电视剧
                episode_count = 24  # 电视剧默认估算24集
            elif item.get('cat_id') == '4':  # 动漫
                episode_count = 12  # 动漫默认估算12集
            elif item.get('cat_id') == '3':  # 综艺
                episode_count = 10  # 综艺默认估算10期
            
            # 确定类型
            type_map = {'1': 'movie', '2': 'tv', '3': 'variety', '4': 'anime'}
            anime_type = type_map.get(item.get('cat_id', '1'), 'tv')
            type_desc_map = {'1': '电影', '2': '电视剧', '3': '综艺', '4': '动漫'}
            type_description = type_desc_map.get(item.get('cat_id', '1'), '未知')
            
            anime_info = {
                "animeTitle": item.get('titleTxt', ''),
                "rating": float(item.get('score', 0)) if item.get('score') else 0.0,
                "startDate": f"{item.get('year', '2024')}-01-01T00:00:00",
                "isFavorited": False,
                "imageUrl": item.get('cover', ''),
                "bangumiId": item.get('id', ''),
                "typeDescription": type_description,
                "type": anime_type,
                "episodeCount": episode_count,
                "animeId": int(item.get('id', 0))
            }
            animes.append(anime_info)
        
        return {
            "animes": animes,
            "errorCode": 0,
            "success": True,
            "errorMessage": ""
        }
    
    @staticmethod
    def convert_api_search_result(api_data: Dict[str, Any]) -> Dict[str, Any]:
        """转换自定义API搜索结果为DanDanPlay格式"""
        if not api_data or 'results' not in api_data:
            return {"animes": [], "errorCode": 0, "success": True, "errorMessage": ""}
        
        animes = []
        results = api_data.get('results', [])
        
        # 类型映射
        type_map = {
            'movie': 'movie',
            'tv_series': 'tv',
            'variety': 'variety',
            'anime': 'anime'
        }
        
        type_desc_map = {
            'movie': '电影',
            'tv_series': '电视剧', 
            'variety': '综艺',
            'anime': '动漫'
        }
        
        for item in results:
            anime_type = type_map.get(item.get('type', 'tv_series'), 'tv')
            type_description = type_desc_map.get(item.get('type', 'tv_series'), '电视剧')
            
            # 构建bangumiId，包含searchId和result_index信息
            bangumi_id = f"{api_data.get('searchId', '')}_{item.get('result_index', 0)}"
            
            anime_info = {
                "animeTitle": item.get('title', ''),
                "rating": 0.0,  # API数据中没有评分信息
                "startDate": f"{item.get('year', '2024')}-01-01T00:00:00",
                "isFavorited": False,
                "imageUrl": item.get('imageUrl', ''),
                "bangumiId": bangumi_id,
                "typeDescription": type_description,
                "type": anime_type,
                "episodeCount": item.get('episodeCount', 0),
                "animeId": hash(bangumi_id) % 2147483647,  # 生成数字ID
                # 保存原始数据用于后续详情获取
                "_searchId": api_data.get('searchId', ''),
                "_resultIndex": item.get('result_index', 0)
            }
            animes.append(anime_info)
        
        return {
            "animes": animes,
            "errorCode": 0,
            "success": True,
            "errorMessage": ""
        }
    
    @staticmethod
    def convert_360_bangumi_detail(bangumi_data: Dict[str, Any], bangumi_id: str) -> Dict[str, Any]:
        """转换360番剧详情为DanDanPlay格式（保持原有逻辑）"""
        # 这里保持原有的convert_to_dandanplay_bangumi逻辑
        # 由于代码较长，这里先返回空，在主文件中处理
        return None
    
    @staticmethod
    def convert_api_bangumi_detail(episodes_data: List[Dict[str, Any]], bangumi_info: Dict[str, Any], bangumi_id: str = None) -> Dict[str, Any]:
        """转换自定义API剧集详情为DanDanPlay格式"""
        if not episodes_data:
            return {"errorCode": 404, "success": False, "errorMessage": "剧集不存在"}
        
        episodes = []
        # 优先使用传入的bangumi_id参数，如果没有则从bangumi_info获取
        if bangumi_id is None:
            bangumi_id = bangumi_info.get('bangumiId', '')
        
        for episode in episodes_data:
            episode_index = episode.get('episodeIndex', 1)
            # 使用bangumi_id的hash + episode_index确保全局唯一
            bangumi_hash = abs(hash(bangumi_id)) % 100000
            episode_id = int(f"{bangumi_hash}{str(episode_index).zfill(3)}")
            
            episode_info = {
                "lastWatched": None,
                "episodeTitle": episode.get('title', f"第{episode_index}话"),
                "seasonId": None,
                "episodeNumber": str(episode_index),
                "episodeId": episode_id,
                "airDate": f"{bangumi_info.get('year', '2024')}-01-01T00:00:00"
            }
            episodes.append(episode_info)
        
        # 构建完整的bangumi信息
        bangumi_detail = {
            "bangumi": {
                "rating": 0.0,
                "isOnAir": True,
                "metadata": [
                    f"中文名: {bangumi_info.get('title', '')}",
                    f"年份: {bangumi_info.get('year', '')}",
                    f"平台: {episodes_data[0].get('provider', '') if episodes_data else ''}",
                    f"类型: {bangumi_info.get('type', '')}"
                ],
                "userRating": 0,
                "summary": f"共{len(episodes_data)}集",
                "relateds": [],
                "tags": [],
                "similars": [],
                "isRestricted": False,
                "intro": f"类型：{bangumi_info.get('type', '')}",
                "bangumiUrl": "",
                "seasons": [],
                "bangumiId": bangumi_id,
                "type": "tv" if bangumi_info.get('type') != 'movie' else "movie",
                "imageUrl": bangumi_info.get('imageUrl', ''),
                "animeId": bangumi_info.get('animeId', 0),
                "episodes": episodes,
                "animeTitle": bangumi_info.get('title', ''),
                "onlineDatabases": [],
                "searchKeyword": bangumi_info.get('title', ''),
                "isFavorited": False,
                "airDay": 1,
                "titles": [
                    {
                        "title": bangumi_info.get('title', ''),
                        "language": "主标题"
                    }
                ],
                "ratingDetails": {},
                "typeDescription": bangumi_info.get('typeDescription', ''),
                "comment": "",
                "favoriteStatus": None,
                "trailers": []
            },
            "errorCode": 0,
            "success": True,
            "errorMessage": ""
        }
        
        return bangumi_detail
