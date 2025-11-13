from dataclasses import dataclass
from typing import List


@dataclass
class VideoDataDto:
    title: str
    season_number: int
    source: str  # 来源
    url: List[str]
    img_url: str
    episodeCount: int
