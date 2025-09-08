import json
import redis
import requests
from flask import Blueprint, request, jsonify

from Fuction import request_data
from apps.danmu.app import download_barrage
from core.danmu.danmuType import RetDanMuType

dandanplay_app = Blueprint('dandanplay', __name__, url_prefix='/dandanplay')

# Redis配置 - 全内存模式
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# 配置Redis为全内存模式
try:
    redis_client.config_set('save', '')  # 禁用RDB持久化
    redis_client.config_set('appendonly', 'no')  # 禁用AOF持久化
    print("Redis已配置为全内存模式")
except Exception as e:
    print(f"Redis配置失败: {e}")

def search_360_api(keyword):
    """调用360搜索API"""
    url = f"https://api.so.360kan.com/index?kw={keyword}&from&pageno=1&v_ap=1&tab=all"
    try:
        response = request_data("GET", url, impersonate='chrome124')
        return response.json()
    except Exception as e:
        print(f"360搜索API调用失败: {e}")
        return None

def convert_to_dandanplay_anime_list(search_data):
    """将360搜索结果转换为DanDanPlay search/anime格式"""
    if not search_data or 'data' not in search_data:
        return {"animes": [], "errorCode": 0, "success": True, "errorMessage": ""}
    
    animes = []
    rows = search_data.get('data', {}).get('longData', {}).get('rows', [])
    
    for item in rows:
        # 计算集数
        episode_count = 1  # 默认1集（电影）
        if item.get('cat_id') == '2' and item.get('seriesPlaylinks'):  # 电视剧
            episode_count = len([link for link in item.get('seriesPlaylinks', []) if isinstance(link, dict)])
        elif item.get('coverInfo', {}).get('txt'):
            # 从coverInfo提取集数信息
            cover_text = item.get('coverInfo', {}).get('txt', '')
            if '集' in cover_text:
                try:
                    episode_count = int(cover_text.replace('全', '').replace('更新至', '').replace('集', ''))
                except:
                    episode_count = 1
        
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

def convert_to_dandanplay_bangumi(bangumi_data, bangumi_id):
    """将360搜索单个结果转换为DanDanPlay bangumi格式"""
    if not bangumi_data:
        return {"errorCode": 404, "success": False, "errorMessage": "番剧不存在"}
    
    # 生成episodes列表
    episodes = []
    
    if bangumi_data.get('cat_id') == '1':  # 电影
        episodes.append({
            "lastWatched": None,
            "episodeTitle": "movie",
            "seasonId": None,
            "episodeNumber": "movie",
            "episodeId": int(f"{bangumi_id}001"),
            "airDate": f"{bangumi_data.get('year', '2024')}-01-01T00:00:00"
        })
    else:  # 电视剧/动漫/综艺
        series_links = bangumi_data.get('seriesPlaylinks', [])
        for idx, link in enumerate(series_links, 1):
            if isinstance(link, dict):
                episodes.append({
                    "lastWatched": None,
                    "episodeTitle": f"第{idx}话",
                    "seasonId": None,
                    "episodeNumber": str(idx),
                    "episodeId": int(f"{bangumi_id}{str(idx).zfill(3)}"),
                    "airDate": f"{bangumi_data.get('year', '2024')}-01-01T00:00:00"
                })
    
    # 构建完整的bangumi信息
    bangumi_info = {
        "bangumi": {
            "rating": float(bangumi_data.get('score', 0)) if bangumi_data.get('score') else 0.0,
            "isOnAir": True,
            "metadata": [
                f"中文名: {bangumi_data.get('titleTxt', '')}",
                f"年份: {bangumi_data.get('year', '')}",
                f"地区: {', '.join(bangumi_data.get('area', []))}",
                f"标签: {', '.join(bangumi_data.get('tag', []))}",
                f"导演: {', '.join(bangumi_data.get('dirList', []))}",
                f"主演: {', '.join(bangumi_data.get('actList', [])[:10])}"  # 限制演员数量
            ],
            "userRating": 0,
            "summary": bangumi_data.get('description', ''),
            "relateds": [],
            "tags": [{"id": i+1, "name": tag, "count": 100} for i, tag in enumerate(bangumi_data.get('tag', []))],
            "similars": [],
            "isRestricted": False,
            "intro": f"分类：{bangumi_data.get('cat_name', '')}",
            "bangumiUrl": bangumi_data.get('url', ''),
            "seasons": [],
            "bangumiId": bangumi_id,
            "type": "tv" if bangumi_data.get('cat_id') != '1' else "movie",
            "imageUrl": bangumi_data.get('cover', ''),
            "animeId": int(bangumi_id),
            "episodes": episodes,
            "animeTitle": bangumi_data.get('titleTxt', ''),
            "onlineDatabases": [],
            "searchKeyword": bangumi_data.get('titleTxt', ''),
            "isFavorited": False,
            "airDay": 1,
            "titles": [
                {
                    "title": bangumi_data.get('titleTxt', ''),
                    "language": "主标题"
                }
            ],
            "ratingDetails": {},
            "typeDescription": bangumi_data.get('cat_name', ''),
            "comment": "",
            "favoriteStatus": None,
            "trailers": []
        },
        "errorCode": 0,
        "success": True,
        "errorMessage": ""
    }
    
    return bangumi_info

def get_episode_url_by_id(episode_id):
    """根据episodeId获取播放链接"""
    # 解析episodeId: {bangumiId}{episode_number}
    episode_id_str = str(episode_id)
    
    if len(episode_id_str) < 4:
        return None
        
    # 提取bangumiId和集数
    bangumi_id = episode_id_str[:-3]  # 去掉最后3位
    episode_num = int(episode_id_str[-3:])  # 最后3位是集数
    
    # 从Redis获取番剧数据
    cache_key = f"dandanplay:bangumi:{bangumi_id}"
    cached_data = redis_client.get(cache_key)
    
    if not cached_data:
        return None
    
    try:
        bangumi_data = json.loads(cached_data)
    except:
        return None
    
    # 获取对应集数的URL
    if bangumi_data.get('cat_id') == '1':  # 电影
        playlinks = bangumi_data.get('playlinks', {})
        if playlinks:
            return list(playlinks.values())[0]  # 返回第一个播放链接
    else:  # 电视剧等
        series_links = bangumi_data.get('seriesPlaylinks', [])
        if episode_num <= len(series_links):
            link_data = series_links[episode_num - 1]
            if isinstance(link_data, dict):
                return link_data.get('url')
            else:
                return link_data  # 直接是URL字符串
    
    return None

@dandanplay_app.route('/api/v2/search/anime')
def search_anime():
    """搜索动漫/影视资源"""
    keyword = request.args.get('keyword')
    if not keyword:
        return jsonify({"animes": [], "errorCode": 400, "success": False, "errorMessage": "缺少keyword参数"})
    
    # 调用360搜索API
    search_result = search_360_api(keyword)
    if not search_result:
        return jsonify({"animes": [], "errorCode": 500, "success": False, "errorMessage": "搜索失败"})
    
    # 缓存搜索结果到Redis
    rows = search_result.get('data', {}).get('longData', {}).get('rows', [])
    for item in rows:
        bangumi_id = item.get('id')
        if bangumi_id:
            cache_key = f"dandanplay:bangumi:{bangumi_id}"
            redis_client.setex(cache_key, 3600, json.dumps(item))  # 缓存1小时
    
    # 转换为DanDanPlay格式
    result = convert_to_dandanplay_anime_list(search_result)
    return jsonify(result)

@dandanplay_app.route('/api/v2/bangumi/<bangumi_id>')
def get_bangumi(bangumi_id):
    """获取番剧详情和剧集列表"""
    # 从Redis获取缓存数据
    cache_key = f"dandanplay:bangumi:{bangumi_id}"
    cached_data = redis_client.get(cache_key)
    
    if not cached_data:
        return jsonify({"errorCode": 404, "success": False, "errorMessage": "番剧不存在或缓存已过期"})
    
    try:
        bangumi_data = json.loads(cached_data)
    except:
        return jsonify({"errorCode": 500, "success": False, "errorMessage": "数据解析失败"})
    
    # 转换为DanDanPlay格式
    result = convert_to_dandanplay_bangumi(bangumi_data, bangumi_id)
    return jsonify(result)

@dandanplay_app.route('/api/v2/comment/<int:episode_id>')
def get_comments(episode_id):
    """获取剧集弹幕"""
    ch_convert = request.args.get('chConvert', '0')
    with_related = request.args.get('withRelated', 'true')
    
    # 根据episodeId获取播放URL
    play_url = get_episode_url_by_id(episode_id)
    if not play_url:
        return jsonify({
            "count": 0,
            "comments": []
        })
    
    try:
        # 使用现有的弹幕获取系统
        danmu_data: RetDanMuType = download_barrage(play_url)
        if not danmu_data:
            return jsonify({
                "count": 0,
                "comments": []
            })
        
        # 转换为DanDanPlay格式
        comments = []
        for idx, item in enumerate(danmu_data.list):
            item_dict = item.__dict__()
            
            # 构建p参数: 时间,模式,颜色,[来源]
            mode = 1  # 默认滚动弹幕
            if hasattr(item, 'mode'):
                mode = item.mode
            
            # 处理颜色格式
            color = item_dict.get("color", "#FFFFFF")
            if color.startswith("#"):
                color = str(int(color[1:], 16))  # 转为十进制
            else:
                color = "16777215"  # 默认白色
            
            # 格式化时间，保留两位小数
            time_str = f"{float(item_dict['time']):.2f}"
            
            # 添加来源信息
            source = item_dict.get("source", "unknown")
            if not source or source == "unknown":
                source = "360kan"  # 默认来源
            
            # 构建完整的p参数: 时间,模式,颜色,[来源]
            p_param = f"{time_str},{mode},{color},[{source}]"
            
            comment = {
                "cid": idx,
                "p": p_param,
                "m": item_dict["text"]
            }
            comments.append(comment)
        
        return jsonify({
            "count": len(comments),
            "comments": comments
        })
        
    except Exception as e:
        print(f"获取弹幕失败: {e}")
        return jsonify({
            "count": 0,
            "comments": []
        })
