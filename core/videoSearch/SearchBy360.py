import re
from typing import List

import cn2an

from Fuction import request_data
from core.videoSearch.Base import VideoSearchBase
from core.videoSearch.videoSearchType import VideoDataDto


class SearchBy360(VideoSearchBase):
    def __init__(self, ):
        super().__init__()

    def main(self, name: str) -> List[VideoDataDto]:
        url = f"https://api.so.360kan.com/index?kw={name}&from&pageno=1&v_ap=1&tab=all"
        res = request_data("GET", url, impersonate='chrome124')
        json_data = res.json()
        video_list = []
        if (json_data.get('data', {}).get('longData') == []):
            return video_list
        for item in json_data.get('data', {}).get('longData', {}).get('rows', []):
            if item.get('playlinks', {}) == {}:
                continue
            title = item.get('titleTxt', '')
            img_url = item.get('cover', '')
            d_tv_num = re.findall("第(.*?)季", title)
            if not d_tv_num:
                d_tv_num = re.findall(rf'{re.escape(name)}(\d+)', title)
            if not d_tv_num:
                roman_num = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"]
                roman_num_str = '|'.join(roman_num)
                _d_tv_num = re.findall(f'{re.escape(name)}([{roman_num_str}]+)', title)
                if _d_tv_num:
                    d_tv_num = [roman_num.index(_d_tv_num[0])]
            if not d_tv_num:
                d_tv_num = "一"
            else:
                d_tv_num = d_tv_num[0]
            try:
                d_tv_num = cn2an.an2cn(int(d_tv_num))

            except:
                pass
            url_list = []
            episode_count = len(item.get('seriesPlaylinks', []))

            for v in item.get('seriesPlaylinks', []):
                if type(v) == str:
                    url_list.append(v)
                else:
                    url_list.append(v.get('url'))
            if len(url_list) == 0:
                for k, v in item.get("playlinks", {}).items():
                    if type(v) == str:
                        url_list.append(v)
                    elif type(v) == list:
                        for i in v:
                            if i.get("url"):
                                url_list.append(i.get('url'))
                        episode_count = len(v)
            video_data = VideoDataDto(
                title=title,
                season_number=cn2an.cn2an(d_tv_num),
                source="360kan",
                url=url_list,
                img_url=img_url,
                episodeCount=episode_count
            )
            video_list.append(video_data)
        return video_list


if __name__ == '__main__':
    SearchBy360().get("爱情公寓")
