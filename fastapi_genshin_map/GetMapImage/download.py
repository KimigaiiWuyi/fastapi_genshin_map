import aiofiles
import aiohttp
from httpx import AsyncClient
from PIL import Image
import asyncio
from .logger import logger
from pathlib import Path

slice_path = Path(__file__).parent / 'slice_data'
slice_path.mkdir(parents=True, exist_ok=True)

BASE = 'https://act-webstatic.mihoyo.com/ys-map-op/map'

world = {
    2: '/2/253e4ea4c79eb920429e26720cebf6ef',
    7: '/7/2d0a83cf40ca8f5a2ef0b1a5199fc407',
    9: '/9/96733f1194aed673f3cdafee4f56b2d2',
    34: '/34/9af6a4747bab91f96c598f8e8a9b7ce5',
}

x, y = 0, 0


async def download_file(url, save_path):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
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
    resp = await client.get(URL.format(f'{i}_{j}'))
    if resp.status_code != 200:
        return

    if x < i:
        x = i
    if y < j:
        y = j

    async with aiofiles.open(slice_path / f'{map_id}_{i}_{j}.webp', 'wb') as f:
        await f.write(resp.read())

    logger.info(f'请求成功，文件 [{map_id}] | {i}_{j}.webp 已保存！')


async def make_P0_map(map_id: int) -> Image.Image:
    global x, y

    async with AsyncClient() as client:
        TASK = []
        for i in range(0, 72):
            for j in range(0, 72):
                if (slice_path / f'{map_id}_{i}_{j}.webp').exists():
                    logger.info(f'文件 {map_id}_{i}_{j}.webp 已存在！跳过下载..')
                    if x < i:
                        x = i
                    if y < j:
                        y = j
                    continue

                TASK.append(download_P0_img(client, map_id, i, j))
                if len(TASK) >= 15:
                    await asyncio.gather(*TASK)
                    await asyncio.sleep(0.5)
                    TASK.clear()
        if TASK:
            await asyncio.gather(*TASK)
            TASK.clear()

    big_img = Image.new('RGBA', (x * 256 + 2048, y * 256 + 1024))

    logger.info(f'【{map_id}切片下载完成, 开始合并】x: {x}, y: {y}')
    for i in range(x):
        for j in range(y):
            logger.info(f'合并: {i} {j}')
            img = Image.open(slice_path / f'{map_id}_{i}_{j}.webp')
            img = img.convert('RGBA')
            big_img.paste(img, (i * 256 + 2048, j * 256 + 1024), img)

    return big_img
