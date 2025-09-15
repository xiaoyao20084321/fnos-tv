from typing import List

import cn2an


class VideoSearchBase(object):

    def get(self, name: str, tv_num: str, season) -> List[str]:
        if tv_num is None:
            tv_num = "一"
        else:
            try:
                tv_num = cn2an.an2cn(int(tv_num))
            except (ValueError, TypeError):
                # 如果转换失败，保持原样
                pass
        ret = self.main(name, tv_num, season)
        return ret

    def main(self, name: str, tv_num: str, season) -> List[str] | None:
        """
        搜索的主要逻辑，返回一个链接
        :return: 
        """
        pass
