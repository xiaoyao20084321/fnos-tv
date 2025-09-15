import re
from typing import List

import cn2an

from Fuction import request_data
from core.videoSearch.Base import VideoSearchBase


class SearchBy360(VideoSearchBase):
    def __init__(self, ):
        super().__init__()

    def main(self, name: str, tv_num: str, season) -> List[str] | None:
        url = f"https://api.so.360kan.com/index?kw={name}&from&pageno=1&v_ap=1&tab=all"
        res = request_data("GET", url, impersonate='chrome124')
        json_data = res.json()
        for item in json_data.get('data', {}).get('longData', {}).get('rows', []):
            if item.get('playlinks', {}) == {}:
                continue
            title = item.get('titleTxt', '')
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
            if name.split(" ")[0] in title and (tv_num == name or d_tv_num == tv_num):
                if (season and int(item.get('cat_id')) >= 2) or (not season and int(item.get('cat_id')) < 2):
                    url_list = []
                    for k, v in item.get('playlinks').items():
                        url_list.append(v)
                    return url_list
