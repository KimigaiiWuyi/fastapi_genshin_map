import random
from io import BytesIO
from pathlib import Path
from time import time
from typing import Optional, Union

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from PIL import Image

from .GenshinMap.genshinmap import img, models, request, utils
from .logger import logger

Image.MAX_IMAGE_PIXELS = 333120000
router = APIRouter(prefix='/get_map')
TEXT_PATH = Path(__file__).parent / 'texture2d'
mark_quest = Image.open(TEXT_PATH / 'mark_quest.png').resize((32, 32))
MAP = Path(__file__).parent / 'map_data'
RESOURCE_PATH = Path(__file__).parent / 'resource_data'
CHASM_PATH = MAP / 'chasm.png'
ENKANOMIYA_PATH = MAP / 'enkanomiya.png'
TEYVAT_PATH = MAP / 'teyvat.png'


MAP_ID_DICT = {
    '2': models.MapID.teyvat,  # 提瓦特
    '9': models.MapID.chasm,  # 层岩巨渊
    '7': models.MapID.enkanomiya,  # 渊下宫
    # MapID.golden_apple_archipelago,  # 金苹果群岛
}


@router.on_event('startup')
async def create_genshin_map():
    if CHASM_PATH.exists() and ENKANOMIYA_PATH.exists() and TEYVAT_PATH.exists():
        logger.info('****************** 开始地图API服务 *****************')
        return
    logger.info('****************** 地图API服务进行初始化 *****************')
    mark_god_pic = Image.open(TEXT_PATH / 'mark_god.png')
    mark_trans_pic = Image.open(TEXT_PATH / 'mark_trans.png')
    for map_id in models.MapID:
        maps = await request.get_maps(map_id)
        points = await request.get_points(map_id)
        # 获取七天神像锚点
        mark_god = utils.get_points_by_id(2, points)
        # 获取传送锚点
        mark_trans = utils.get_points_by_id(3, points)
        # 转换两个锚点为标准坐标
        mark_god_converted = utils.convert_pos(mark_god, maps.detail.origin)
        mark_trans_converted = utils.convert_pos(mark_trans, maps.detail.origin)
        maps = await request.get_maps(map_id)
        map_img = await utils.make_map(maps.detail)
        for mark_god_point in mark_god_converted:
            map_img.paste(
                mark_god_pic,
                (int(mark_god_point.x) - 32, int(mark_god_point.y) - 64),
                mark_god_pic,
            )
        for mark_trans_point in mark_trans_converted:
            map_img.paste(
                mark_trans_pic,
                (int(mark_trans_point.x) - 32, int(mark_trans_point.y) - 64),
                mark_trans_pic,
            )
        if not MAP.exists():
            MAP.mkdir()
        map_img.save(MAP / f'{map_id.name}.png')
    logger.info('****************** 开始地图API服务 *****************')


@router.get('')
async def get_map_by_point(
    resource_name: str = '甜甜花',
    map_id: Union[str, int] = 2,
    is_cluster: bool = False,
):
    req_id = random.randint(10000, 99999)
    prefix = f'>> [请求序列:{req_id}]'
    logger.info(f'{prefix} 收到资源点访问请求! [资源名称] {resource_name} [地图ID] {map_id}')
    ERROR = {
        'retcode': -1,
        'message': f'该资源点 - {resource_name} 不存在!',
    }
    # 校验map_id有效性
    if map_id not in MAP_ID_DICT:
        logger.warning(f'{prefix} 请求失败! 原因: 该地图ID [{map_id}] 不存在!')
        return {
            'retcode': -1,
            'message': f'该地图ID - {map_id} 不存在!',
        }

    # 寻找主地图的缓存
    map_data = MAP_ID_DICT[map_id]
    map_path = MAP / f'{map_data.name}.png'

    # 寻找保存点
    if not RESOURCE_PATH.exists():
        RESOURCE_PATH.mkdir()
    if is_cluster:
        save_path = RESOURCE_PATH / f'{map_data.name}_{resource_name}_KMEANS.jpg'
    else:
        save_path = RESOURCE_PATH / f'{map_data.name}_{resource_name}.jpg'

    # 如果存在缓存,直接回复
    if save_path.exists():
        logger.info(f'{prefix} [成功] [资源名称] {resource_name} 已有缓存, 直接发送!')
        return FileResponse(save_path)

    logger.info(f'{prefix} [资源名称] {resource_name} 暂无缓存, 开始执行绘制...')
    maps = await request.get_maps(map_id)
    labels = await request.get_labels(map_id)

    # 请求资源ID
    resource_id = 0
    for label in labels:
        for child in label.children:
            if resource_name == child.name:
                resource_id = child.id
                resource_name = child.name
                break

    if resource_id == 0:
        logger.warning(f'{prefix} 请求失败! 原因: 该资源点 [{resource_name}] 不存在!')
        return ERROR

    # 请求坐标点
    points = await request.get_points(map_id)
    transmittable = utils.get_points_by_id(resource_id, points)

    # 转换坐标
    transmittable_converted = utils.convert_pos(transmittable, maps.detail.origin)

    # 进行最密点获取
    if is_cluster:
        group_point = img.k_means_points(transmittable_converted)
    else:
        # 如果资源点不存在,返回错误
        if len(transmittable_converted) == 0:
            return ERROR
        else:
            # 计算极限坐标
            up = 20000
            down = 0
            left = 20000
            right = 0
            for point in transmittable_converted:
                if point.x >= right:
                    right = point.x
                if point.x <= left:
                    left = point.x
                if point.y >= down:
                    down = point.y
                if point.y <= up:
                    up = point.y
            offset = 100
            group_point = [
                [
                    models.XYPoint(left - offset, up - offset),
                    models.XYPoint(right + offset, down + offset),
                    transmittable_converted,
                ]
            ]

    # 打开主地图
    genshin_map = Image.open(map_path)

    # 计算裁切点
    lt_point = group_point[0][0]
    rb_point = group_point[0][1]

    # 开始裁切
    genshin_map = genshin_map.crop(
        (int(lt_point.x), int(lt_point.y), int(rb_point.x), int(rb_point.y))
    )

    # 在地图上绘制资源点
    for point in group_point[0][2]:
        point_trans = (
            int(point.x) - int(lt_point.x),
            int(point.y) - int(lt_point.y),
        )
        genshin_map.paste(
            mark_quest, (point_trans[0] - 16, point_trans[1] - 16), mark_quest
        )

    # 转换RGB图
    genshin_map = genshin_map.convert('RGB')

    # 转为Bytes,暂时废弃
    # result_buffer = BytesIO()
    # genshin_map.save(result_buffer, format='PNG', quality=80, subsampling=0)

    # 进行保存
    genshin_map.save(save_path, 'JPEG', quality=85)
    logger.info(f'{prefix} [成功] [资源名称] {resource_name} 绘制完成!')
    return FileResponse(save_path)
