from dataclasses import dataclass
from typing import List
from typing import Generic, TypeVar

import core.videoSearch
from core.videoSearch import videoSearchType

T = TypeVar("T")


@dataclass
class DandanRetBase(Generic[T]):
    errorCode: int
    success: bool
    errorMessage: str
    data: T


@dataclass
class SeasonDataDto:
    id: str
    title: str  # 标题
    episodeCount: int  # 剧集数量
    summary: str  # 介绍


@dataclass
class EpisodeDto:
    episodeId: int
    episodeTitle: str  # 剧集标题
    episodeNumber: str  # 第几集
    seasonId: str


@dataclass
class VideoDataDto:
    title: str
    season_number: int
    episode_number: int
    episode_title: str
    source: str  # 来源
    seasons: List[SeasonDataDto]
    episodes: List[EpisodeDto]


@dataclass
class AnimeRetDto:
    animeId: int
    bangumiId: str
    animeTitle: str
    type: str
    imageUrl: str  # 
    episodeCount: int  # 

    @classmethod
    def VideoDataDto2AnimeRetDto(cls, data: videoSearchType.VideoDataDto):
        return cls(
            animeTitle=data.title,
            imageUrl=data.img_url,
            type=data.source,
            episodeCount=data.episodeCount,
            animeId=0,
            bangumiId='',
        )
