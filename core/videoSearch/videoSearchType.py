from dataclasses import dataclass
from typing import List


@dataclass
class VideoDataDto:
    title: str
    season_number: int
    episode_number: int
    episode_title: str
    source: str  # 来源
    url: str
