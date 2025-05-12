import random
from pathlib import Path
from typing import Optional, Union

import yaml
from fastapi import APIRouter
from fastapi.responses import FileResponse
from PIL import Image

from .GenshinMap.genshinmap import img, models, request, utils
from .logger import logger
from .download import download_file, make_P0_map

Image.MAX_IMAGE_PIXELS = 603120000
router = APIRouter(prefix='/get_map')
TEXT_PATH = Path(__file__).parent / 'texture2d'
mark_quest = Image.open(TEXT_PATH / 'mark_quest.png').resize((32, 32))
MAP = Path(__file__).parent / 'map_data'
RESOURCE_PATH = Path(__file__).parent / 'resource_data'
ICON_PATH = Path(__file__).parent / 'icon_data'

_path = Path(__file__).parent / 'map.yaml'
with open(_path, 'r', encoding='utf-8') as ymlfile:
    resource_aliases = yaml.load(ymlfile, Loader=yaml.SafeLoader)

MAP_ID_DICT = {
    '2': models.MapID.teyvat,  # 提瓦特
    '9': models.MapID.chasm,  # 层岩巨渊
    '7': models.MapID.enkanomiya,  # 渊下宫
    '34': models.MapID.sea_of_bygone_eras,  # 旧日之海
    '36': models.MapID.holy_mountain,  # 远古圣山
    # MapID.golden_apple_archipelago,  # 金苹果群岛
}

if not ICON_PATH.exists():
    ICON_PATH.mkdir(exist_ok=True)


# 校验地图文件是否下载
def check_map_file():
    for map_id in MAP_ID_DICT.values():
        map_path = MAP / f'{map_id.name}.png'
        if not map_path.exists():
            logger.info(f'地图文件 {map_path} 不存在')
            return False
    return True


@router.on_event('startup')
async def create_genshin_map():
    if check_map_file():
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
        mark_god_converted = utils.convert_pos(
            mark_god,
            maps.get_detail.origin,
        )
        mark_trans_converted = utils.convert_pos(
            mark_trans,
            maps.get_detail.origin,
        )
        maps = await request.get_maps(map_id)
        # map_img = await utils.make_map(maps.detail)
        map_img = await make_P0_map(maps.id, maps.get_detail)
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
        logger.info('****************** 开始绘制 *****************')
        trees = await request.get_labels(map_id)
        '''
        for tree in trees:
            for label in tree.children:
                await get_map_response(
                    'PRE-START',
                    label.name,
                    map_id,
                    False,
                )
        '''
        # 改成并发
        import asyncio

        tasks = []
        for tree in trees:
            for label in tree.children:
                tasks.append(
                    get_map_response(
                        'PRE-START',
                        label.name,
                        map_id,
                        False,
                    )
                )
        await asyncio.gather(*tasks)
    logger.info('****************** 开始地图API服务 *****************')


async def get_map_response(
    prefix: str,
    resource_name: str,
    map_id: models.MapID,
    is_cluster: bool = False,
) -> Optional[Path]:
    # 寻找主地图的缓存
    map_path = MAP / f'{map_id.name}.png'
    if '/' in resource_name:
        resource_name = resource_name.replace('/', '_')

    # 寻找保存点
    if not RESOURCE_PATH.exists():
        RESOURCE_PATH.mkdir()
    if is_cluster:
        save_path = RESOURCE_PATH / f'{map_id.name}_{resource_name}_KMEANS.jpg'
    else:
        save_path = RESOURCE_PATH / f'{map_id.name}_{resource_name}.jpg'

    # 如果存在缓存,直接回复
    if save_path.exists():
        logger.info(f'{prefix} [查询成功]：发送缓存 [{save_path.name}]！')
        return save_path

    maps = await request.get_maps(map_id)
    trees = await request.get_labels(map_id)

    # 请求资源ID
    resource_id = 0
    for tree in trees:
        for label in tree.children:
            if resource_name == label.name:
                resource_id = label.id
                resource_name = label.name
                icon = label.icon
                break
        else:
            if resource_name == tree.name:
                resource_id = tree.id
                resource_name = tree.name
                icon = tree.icon
                break

    if resource_id == 0:
        return

    # 请求坐标点
    points = await request.get_points(map_id)
    transmittable = utils.get_points_by_id(resource_id, points)

    # 转换坐标
    transmittable_converted = utils.convert_pos(
        transmittable,
        maps.get_detail.origin,
    )

    # 进行最密点获取
    if is_cluster:
        group_point = img.k_means_points(transmittable_converted)
    else:
        # 如果资源点不存在,返回错误
        if len(transmittable_converted) == 0:
            return
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

    logger.info(f'{prefix} [新增缓存]：开始绘制 {save_path.name}...')
    # 打开主地图
    genshin_map = Image.open(map_path)

    # 计算裁切点
    lt_point = group_point[0][0]
    rb_point = group_point[0][1]

    # 增加裁切长宽
    x = rb_point[0] - lt_point[0]
    y = rb_point[1] - lt_point[1]
    if x < 500 or y < 500:
        lt_point = models.XYPoint(lt_point.x - 400, lt_point.y - 400)
        rb_point = models.XYPoint(rb_point.x + 400, rb_point.y + 400)

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

        icon_path = ICON_PATH / f'{resource_name}.png'
        while True:
            try:
                if not icon_path.exists():
                    await download_file(icon, icon_path)
                icon_pic = Image.open(icon_path).resize((52, 52))
            except:  # noqa: E722
                await download_file(icon, icon_path)
                continue
            break

        if point.s == 1:  # type: ignore
            z = 1
        else:
            z = point.z  # type: ignore

        if z <= 3:
            mark = Image.open(TEXT_PATH / f'mark_{z}.png')
        else:
            mark = Image.open(TEXT_PATH / 'mark_B.png')

        _m = None
        if point.s == 1:  # type: ignore
            _m = Image.open(TEXT_PATH / 'B.png')
        elif point.s == 3:  # type: ignore
            _m = Image.open(TEXT_PATH / 'W.png')
        if _m is not None:
            mark.paste(_m, (13, 50), _m)

        icon_pic = icon_pic.convert('RGBA')
        mark.paste(icon_pic, (25, 17), icon_pic)

        mark_size = (70, 70)
        mark = mark.resize(mark_size)

        genshin_map.paste(
            mark,
            (
                point_trans[0] - mark_size[0] // 2,
                point_trans[1] - mark_size[1],
            ),
            mark,
        )

    # 转换RGB图
    genshin_map = genshin_map.convert('RGB')

    # 转为Bytes,暂时废弃
    # result_buffer = BytesIO()
    # genshin_map.save(result_buffer, format='PNG', quality=80, subsampling=0)

    # 进行保存
    genshin_map.save(save_path, 'JPEG', quality=95)
    logger.info(f'{prefix} [查询成功]：新增缓存 [{save_path.name}]！')
    return save_path


@router.get('')
async def get_map_by_point(
    resource_name: str = '甜甜花',
    map_id: Union[str, int] = 0,
    is_cluster: bool = False,
):
    req_id = random.randint(10000, 99999)

    def resource_aliases_to_name(resource_name: str) -> str:
        resource_name = resource_name.lower()
        for m in resource_aliases:
            for a in resource_aliases[m]:
                if resource_name == a:
                    return a
                if resource_name in resource_aliases[m][a]:
                    return a
        return resource_name

    # 判断别名
    resource_name = resource_aliases_to_name(resource_name)

    prefix = f'>> [请求序列:{req_id}]'
    logger.info(
        f"{prefix} [查询请求]：在地图 ID {map_id or 'auto'} 内查询 {resource_name}..."
    )

    if map_id:
        # 校验 map_id 有效性
        if map_id not in MAP_ID_DICT:
            logger.warning(f'{prefix} [失败]：地图 ID - {map_id} 不存在！')
            return {
                'retcode': -1,
                'message': f'地图 ID - {map_id} 不存在！',
            }
        maps = [MAP_ID_DICT[str(map_id)]]
    else:
        # 自动选择地图
        maps = list(MAP_ID_DICT.values())

    for idx, map in enumerate(maps):
        res = await get_map_response(prefix, resource_name, map, is_cluster)
        if res:
            return FileResponse(res)
        if len(maps) > 1:
            logger.info(
                f'{prefix} [自动重试]：地图 ID {map._value_} 内不存在 {resource_name}...'
            )
    logger.warning(f'{prefix} [失败]：资源点 - {resource_name} 不存在！')
    return {
        'retcode': -1,
        'message': f'资源点 - {resource_name} 不存在！',
    }
