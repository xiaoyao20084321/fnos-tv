import json
import redis
import requests
from flask import Blueprint, request, jsonify

from Fuction import request_data
from apps.danmu.app import download_barrage, get_episode_url
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

def convert_to_dandanplay_bangumi(bangumi_data, bangumi_id):
    """将360搜索单个结果转换为DanDanPlay bangumi格式"""
    if not bangumi_data:
        return {"errorCode": 404, "success": False, "errorMessage": "番剧不存在"}
    
    # 生成episodes列表 - 在bangumi详情阶段进行真正的集数获取
    episodes = []
    
    # 使用playlinks获取真实集数信息（适用于所有类型）
    playlinks = bangumi_data.get('playlinks', {})
    
    if playlinks:
        if bangumi_data.get('cat_id') == '1':  # 电影类型：为每个平台生成一个episode
            movie_title = bangumi_data.get('titleTxt', '电影')
            
            # 平台名称映射
            platform_names = {
                'qq': '腾讯视频',
                'qiyi': '爱奇艺', 
                'youku': '优酷',
                'bilibili1': 'Bilibili',
                'imgo': '芒果TV',
                'leshi': '乐视',
                'm1905': '1905电影网',
                'sohu': '搜狐视频'
            }
            
            episode_index = 1
            for platform_key, platform_url in playlinks.items():
                # 电影类型的playlinks都是简单的字符串格式
                if isinstance(platform_url, str) and platform_url.startswith('http'):
                    platform_name = platform_names.get(platform_key, platform_key.upper())
                    episode_id = int(f"{bangumi_id}{str(episode_index).zfill(3)}")
                    episodes.append({
                        "lastWatched": None,
                        "episodeTitle": f"{movie_title}-{platform_name}",
                        "seasonId": None,
                        "episodeNumber": str(episode_index),
                        "episodeId": episode_id,
                        "airDate": f"{bangumi_data.get('year', '2024')}-01-01T00:00:00"
                    })
                    
                    # 将URL存储到Redis Hash中
                    hash_key = f"dandanplay:episodes:{bangumi_id}"
                    redis_client.hset(hash_key, str(episode_id), platform_url)
                    redis_client.expire(hash_key, 3600)  # 设置1小时过期
                    episode_index += 1
            
        else:  # 电视剧/综艺/动漫：使用get_episode_url获取集数信息
            # 提取和清理playlinks中的URL列表
            platform_url_list = []
            for key, value in playlinks.items():
                
                # 处理不同格式的playlinks数据
                if isinstance(value, str) and value.startswith('http'):
                    # 简单的URL字符串
                    platform_url_list.append(value)
                elif isinstance(value, list):
                    # 字典数组格式，提取其中的url字段
                    for item in value:
                        if isinstance(item, dict) and 'url' in item:
                            if item['url'].startswith('http'):
                                platform_url_list.append(item['url'])
                elif isinstance(value, dict) and 'url' in value:
                    # 单个字典格式
                    if value['url'].startswith('http'):
                        platform_url_list.append(value['url'])
            
            
            # 调用get_episode_url获取集数信息
            if platform_url_list:
                try:
                    print(f"[DEBUG] bangumi调用get_episode_url，URL列表: {platform_url_list}")
                    url_dict = get_episode_url(platform_url_list)
                    print(f"[DEBUG] bangumi get_episode_url返回结果: {url_dict}")
                    
                    if url_dict:
                        # 根据url_dict生成episodes
                        sorted_keys = sorted(url_dict.keys(), key=lambda x: int(x) if x.isdigit() else 0)
                        
                        for ep_key in sorted_keys:
                            try:
                                ep_num = int(ep_key)
                                # 获取该集数对应的真实URL
                                episode_urls = url_dict[ep_key]
                                real_url = episode_urls[0] if isinstance(episode_urls, list) and episode_urls else episode_urls
                                
                                episode_id = int(f"{bangumi_id}{str(ep_num).zfill(3)}")
                                episodes.append({
                                    "lastWatched": None,
                                    "episodeTitle": f"第{ep_num}话",
                                    "seasonId": None,
                                    "episodeNumber": str(ep_num),
                                    "episodeId": episode_id,
                                    "airDate": f"{bangumi_data.get('year', '2024')}-01-01T00:00:00"
                                })
                                
                                # 将URL存储到Redis Hash中
                                hash_key = f"dandanplay:episodes:{bangumi_id}"
                                redis_client.hset(hash_key, str(episode_id), real_url)
                                redis_client.expire(hash_key, 3600)  # 设置1小时过期
                            except ValueError:
                                # 处理非数字的集数标识（如"彩蛋"）
                                episode_urls = url_dict[ep_key]
                                real_url = episode_urls[0] if isinstance(episode_urls, list) and episode_urls else episode_urls
                                
                                episode_id = int(f"{bangumi_id}{str(len(episodes)+1).zfill(3)}")
                                episodes.append({
                                    "lastWatched": None,
                                    "episodeTitle": f"{ep_key}",
                                    "seasonId": None,
                                    "episodeNumber": ep_key,
                                    "episodeId": episode_id,
                                    "airDate": f"{bangumi_data.get('year', '2024')}-01-01T00:00:00"
                                })
                                
                                # 将URL存储到Redis Hash中
                                hash_key = f"dandanplay:episodes:{bangumi_id}"
                                redis_client.hset(hash_key, str(episode_id), real_url)
                                redis_client.expire(hash_key, 3600)  # 设置1小时过期
                    else:
                        pass  # get_episode_url返回空结果
                except Exception:
                    pass  # 静默处理错误
    
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
    """根据episodeId获取播放链接 - 直接从Redis Hash中获取URL"""
    episode_id_str = str(episode_id)
    
    # 遍历所有可能的bangumi Hash来查找URL
    pattern = "dandanplay:episodes:*"
    hash_keys = redis_client.keys(pattern)
    
    for hash_key in hash_keys:
        url = redis_client.hget(hash_key, episode_id_str)
        if url:
            return url
    
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
    # 检查episodes Hash是否已存在（避免并发重复处理）
    episodes_hash_key = f"dandanplay:episodes:{bangumi_id}"
    if redis_client.exists(episodes_hash_key):
        # 已经处理过，从原始缓存重新构建结果
        cache_key = f"dandanplay:bangumi:{bangumi_id}"
        cached_data = redis_client.get(cache_key)
        
        if cached_data:
            try:
                bangumi_data = json.loads(cached_data)
                result = convert_to_dandanplay_bangumi(bangumi_data, bangumi_id)
                return jsonify(result)
            except:
                pass
    
    # 第一次处理或缓存失效，正常处理流程
    cache_key = f"dandanplay:bangumi:{bangumi_id}"
    cached_data = redis_client.get(cache_key)
    
    if not cached_data:
        return jsonify({"errorCode": 404, "success": False, "errorMessage": "番剧不存在或缓存已过期"})
    
    try:
        bangumi_data = json.loads(cached_data)
    except:
        return jsonify({"errorCode": 500, "success": False, "errorMessage": "数据解析失败"})
    
    # 转换为DanDanPlay格式（会处理playlinks并存储到Redis Hash）
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
