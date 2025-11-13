from typing import List

import cn2an

from core.videoSearch.videoSearchType import VideoDataDto


class VideoSearchBase(object):

    def get(self, name: str) -> List[VideoDataDto]:
        ret = self.main(name)
        return ret

    def main(self, name: str) -> List[VideoDataDto]:
        """
        搜索的主要逻辑，返回一个链接
        :return: 
        """
        pass
