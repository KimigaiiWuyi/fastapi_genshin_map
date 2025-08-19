import aiofiles
import aiohttp
from httpx import AsyncClient
from PIL import Image
import asyncio
from .logger import logger
from pathlib import Path
from .GenshinMap.genshinmap.models import DetailV2

slice_path = Path(__file__).parent / 'slice_data'
slice_path.mkdir(parents=True, exist_ok=True)

BASE = 'https://act-webstatic.mihoyo.com/ys-map-op/map'

world = {
    2: '/2/84e91c043f30df2655d34a5543be7b17',
    7: '/7/2d0a83cf40ca8f5a2ef0b1a5199fc407',
    9: '/9/96733f1194aed673f3cdafee4f56b2d2',
    34: '/34/9af6a4747bab91f96c598f8e8a9b7ce5',
    36: '/36/bb19ccbed47e8d9dca730050219d0b90',
}

_map_id = 0
x, y = 0, 0


async def download_file(url, save_path):
    async with aiohttp.ClientSession() as session:
        logger.info(f'开始下载: {url}')
        async with session.get(str(url)) as response:
            if response.status == 200:
                async with aiofiles.open(save_path, "wb") as f:
                    await f.write(await response.read())


async def download_P0_img(
    client: AsyncClient,
    map_id: int,
    i: int,
    j: int,
):
    logger.info(f'当前尝试请求:[{map_id}] | {i} {j}')
    global x, y
    if map_id not in world:
        logger.warning(f'地图 {map_id} 不存在！')
        return

    URL = BASE + world[map_id] + '/{}_P0.webp'
    try:
        resp = await client.get(
            URL.format(f'{i}_{j}'),
            headers={
                'Accept-Encoding': 'deflate',
                'Accept-Ranges': 'bytes',
            },
        )
    except Exception as e:
        logger.warning(f'请求失败, 可能不影响最终结果, 错误信息: {e}')
        return

    if resp.status_code != 200:
        return

    if x < i:
        x = i
    if y < j:
        y = j

    async with aiofiles.open(slice_path / f'{map_id}_{i}_{j}.webp', 'wb') as f:
        await f.write(resp.read())

    logger.info(f'请求成功，文件 [{map_id}] | {i}_{j}.webp 已保存！')


async def make_P0_map(map_id: int, detail_v2: DetailV2) -> Image.Image:
    global x, y, _map_id

    # 左上角x, y區塊座標 (padding) — 可改為 0,0
    x0, y0 = (val // 256 for val in detail_v2.padding)
    # 右下角區塊座標 — 可改models.py裡的calculate_size()為t // 256
    x1, y1 = detail_v2.calculate_size()

    if map_id != _map_id:
        _map_id = map_id
        x, y = 0, 0

    async with AsyncClient() as client:
        TASK = []
        # 自動化下載區塊範圍
        for i in range(x0, x1):
            for j in range(y0, y1):
                if (slice_path / f'{map_id}_{i}_{j}.webp').exists():
                    logger.info(f'文件 {map_id}_{i}_{j}.webp 已存在！跳过下载..')
                    continue
                else:
                    TASK.append(download_P0_img(client, map_id, i, j))
                if len(TASK) >= 15:
                    await asyncio.gather(*TASK)
                    await asyncio.sleep(0.5)
                    TASK.clear()

        if TASK:
            await asyncio.gather(*TASK)
            TASK.clear()

    if map_id == 2:
        ox, oy = 0, 0
    else:
        ox, oy = 0, 0

    x = x1 - x0
    y = y1 - y0
    big_img = Image.new('RGBA', (x * 256 + ox, y * 256 + oy))
    logger.info(f'【{map_id}切片下载完成, 开始合并】x: {x}, y: {y}')

    for i in range(x0, x1):
        for j in range(y0, y1):
            logger.info(f'合并: {i} {j}')
            path = slice_path / f'{map_id}_{i}_{j}.webp'
            if path.exists():
                img = Image.open(path)
            else:
                img = Image.new('RGBA', (256, 256))
            img = img.convert('RGBA')
            big_img.paste(img, (i * 256 + ox, j * 256 + oy), img)

    return big_img
