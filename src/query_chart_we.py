import os
import json
import dotenv
import asyncio

from pkg.plugin.context import EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import *

from .query_song import searchSong
from .utils.wechartutil import WEChartUtil

dotenv.load_dotenv()
SONGS_PATH = os.path.join(os.path.dirname(__file__), "..", os.getenv("SONG_PATH"))
CHART_CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'cache', 'charts')

async def queryChartWE(ctx: EventContext, args: list) -> None:
    '''查询谱面
    
    
    Args:
        ctx (EventContext): 事件上下文
        args (list): 参数列表
    Returns:
        None: 无返回值
    '''
    songs = []
    song = {}
    song_name, type = args
    
    with open(SONGS_PATH, "r", encoding="utf-8-sig") as file:
        songs = json.load(file)
    
    matched_songs = searchSong(song_name)
    
    if len(matched_songs) == 1:
        song = [song for song in songs if song.get('songId') == matched_songs[0]][0]
        song_index = songs.index(song)
    elif len(matched_songs) == 0:
        await ctx.reply(MessageChain([Plain(f"没有找到{song_name}，请尝试输入歌曲全称或其他别名")]))
        return
    else:
        msg_chain = MessageChain([Plain(f"有多个曲目符合条件\n")])
        for songId in matched_songs:
            song_index = songs.index([song for song in songs if song.get('songId') == songId][0])
            msg_chain.append(Plain(f"c{song_index} - {songId}\n"))
        msg_chain.append(Plain(f"\n请使用“chuchart [cid]”进行谱面查询"))
        await ctx.reply(msg_chain)
        return

    '''
    "/chunithm/end/01127end.htm": "/chunithm/chfiles/chlv/star_haya3.png",
    '''

    chartutil = WEChartUtil()
    chartid = chartutil.getChartID(song)
    we_diff = chartutil.getWEDifficulty(chartid, type)
    if chartid == None:
        await ctx.reply(MessageChain([Plain(f"未找到歌曲对应谱面，可能是内部错误或数据未更新")]))
        return
    if we_diff == None:
        await ctx.reply(MessageChain([Plain(f"未找到歌曲对应难度类型：{type}，可能是内部错误或数据未更新")]))
        return
    if chartutil.checkIsHit(chartid, type):
        local_path = os.path.join(CHART_CACHE_DIR, f"{chartid}_{type if type else ''}.png")
        try:
            img_conponent = await Image.from_local(local_path)
        except FileNotFoundError:
            await ctx.reply(MessageChain([Plain(f"未找到歌曲对应谱面，可能是内部错误或数据未更新")]))
            return
        await ctx.reply(MessageChain([
            Plain(f"歌曲 - {song.get('songId')}\n"),
            Plain(f"类型 - {type if type else ''}\n"),
            Plain(f"Artist - {song.get('artist')}\n"),
            img_conponent
        ]))
        return
    else:
        print("[ChunithmUtil] 缓存未命中，开始请求")
        asyncio.create_task(chartutil.getChart(chartid, type, str(ctx.event.launcher_id), song))