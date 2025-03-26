from __future__ import annotations

from enum import IntEnum
from typing import List, Tuple, Optional, NamedTuple

from pydantic import HttpUrl, BaseModel, validator


class MapID(IntEnum):
    """地图 ID"""

    teyvat = 2
    """提瓦特"""
    enkanomiya = 7
    """渊下宫"""
    chasm = 9
    """层岩巨渊·地下矿区"""
    # golden_apple_archipelago = 12
    """金苹果群岛"""
    sea_of_bygone_eras = 34
    """旧日之海"""
    holy_mountain = 36
    """远古圣山"""


class Label(BaseModel):
    id: int
    name: str
    icon: HttpUrl
    parent_id: int
    depth: int
    node_type: int
    jump_type: int
    jump_target_id: int
    display_priority: int
    children: list
    activity_page_label: int
    area_page_label: List[int]
    is_all_area: bool


class Tree(BaseModel):
    id: int
    name: str
    icon: str
    parent_id: int
    depth: int
    node_type: int
    jump_type: int
    jump_target_id: int
    display_priority: int
    children: List[Label]
    activity_page_label: int
    area_page_label: List
    is_all_area: bool


class Point(BaseModel):
    id: int
    label_id: int
    x_pos: float
    y_pos: float
    author_name: str
    ctime: str
    display_state: int
    area_id: int
    ext_attrs: str
    z_level: int
    icon_sign: int


class Slice(BaseModel):
    url: HttpUrl


class Maps(BaseModel):
    slices: Optional[List[HttpUrl]] = None
    origin: Optional[List[int]] = None
    total_size: Optional[List[int]] = None
    padding: Optional[List[int]] = None
    map_version: Optional[str] = None
    min_zoom: Optional[int] = None
    max_zoom: Optional[int] = None
    original_map_size: Optional[List[int]] = None

    @validator("slices", pre=True)
    def slices_to_list(cls, v):
        urls: List[str] = []
        for i in v:
            urls.extend(j["url"] for j in i)
        return urls


class MapInfo(BaseModel):
    id: int
    name: str
    parent_id: int
    depth: int
    detail: Optional[Maps] = None
    detail_v2: Optional[Maps] = None
    node_type: int
    children: list
    icon: Optional[HttpUrl]
    ch_ext: Optional[str]

    @validator("detail", pre=True)
    def detail_str_to_maps(cls, v):
        if not v:
            return None
        return Maps.parse_obj(v)

    @validator("detail_v2", pre=True)
    def detail_v2_str_to_maps(cls, v):
        if not v:
            return None
        return Maps.parse_obj(v)

    @property
    def get_detail(self):
        if self.detail_v2:
            return self.detail_v2
        return self.detail


class XYPoint(NamedTuple):
    x: float
    y: float


class XYZSPoint(NamedTuple):
    x: float
    y: float
    z: int
    s: int


class Kind(BaseModel):
    id: int
    name: str
    icon_id: int
    icon_url: HttpUrl
    is_game: int


class SpotKinds(BaseModel):
    list: List[Kind]
    is_sync: bool
    already_share: bool


class Spot(BaseModel):
    id: int
    name: str
    content: str
    kind_id: int
    spot_icon: str
    x_pos: float
    y_pos: float
    nick_name: str
    avatar_url: HttpUrl
    status: int


class SubAnchor(BaseModel):
    id: int
    name: str
    l_x: int
    l_y: int
    r_x: int
    r_y: int
    app_sn: str
    parent_id: str
    map_id: str
    sort: int


class Anchor(BaseModel):
    id: int
    name: str
    l_x: int
    l_y: int
    r_x: int
    r_y: int
    app_sn: str
    parent_id: str
    map_id: str
    children: List[SubAnchor]
    sort: int

    def get_children_all_left_point(self) -> List[XYPoint]:
        """获取所有子锚点偏左的 `XYPoint` 坐标"""
        return [XYPoint(x=i.l_x, y=i.l_y) for i in self.children]

    def get_children_all_right_point(self) -> List[XYPoint]:
        """获取所有子锚点偏右的 `XYPoint` 坐标"""
        return [XYPoint(x=i.r_x, y=i.r_y) for i in self.children]


class PageLabel(BaseModel):
    id: int
    name: str
    type: int
    pc_icon_url: str
    mobile_icon_url: str
    sort: int
    pc_icon_url2: str
    map_id: int
    jump_url: str
    jump_type: str
    center: Optional[Tuple[float, float]]
    zoom: Optional[float]

    @validator("center", pre=True)
    def center_str_to_tuple(cls, v: str) -> Optional[Tuple[float, float]]:
        if v and (splitted := v.split(",")):
            return tuple(map(float, splitted))  # type: ignore

    @validator("zoom", pre=True)
    def zoom_str_to_float(cls, v: str):
        if v:
            return float(v)
