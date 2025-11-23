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
    name, type = args
    with open(SONGS_PATH, "r", encoding="utf-8-sig") as file:
        songs = json.load(file)
    
    matched_songs = searchSong(name)
    target_songs = []
    cid = None
    if len(matched_songs) == 1:
        target_songs = [song for song in songs if song.get('idx') == matched_songs[0]]
        song = target_songs[0]
        cid = song.get('idx')
    elif len(matched_songs) == 0:
        await ctx.reply(MessageChain([Plain(f"没有找到{name}，请尝试输入歌曲全称或其他别名")]))
        return
    else:
        msg_chain = MessageChain([Plain(f"有多个曲目符合条件\n")])
        for cid in matched_songs:
            name = None
            for song in songs:
                if song.get('idx') == cid:
                    name = song.get('title')
                    break
            msg_chain.append(Plain(f"c{cid} - {name}\n"))
        msg_chain.append(Plain(f"\n请使用cid进行精准查询"))
        await ctx.reply(msg_chain)
        return

    '''
    "/chunithm/end/01127end.htm": "/chunithm/chfiles/chlv/star_haya3.png",
    '''

    chartutil = WEChartUtil()
    chartid = chartutil.getChartID(song)
    # await ctx.reply(MessageChain([Plain(f"chartid: {chartid}")]))
    weprefix = chartutil.getWEPrefix(chartid, type)
    # await ctx.reply(MessageChain([Plain(f"weprefix: {weprefix}")]))
    if chartid == None:
        await ctx.reply(MessageChain([Plain(f"未找到歌曲对应谱面")]))
        return
    if weprefix == []:
        if type != None:
            await ctx.reply(MessageChain([Plain(f"未找到歌曲对应类型：{type}")]))
            return
        else:
            await ctx.reply(MessageChain([Plain(f"此歌曲貌似还没有WE谱")]))
            return
    if type == None and len(weprefix) >= 1:
        types = [chartutil.extractType(chartutil.getValue(prefix)) for prefix in weprefix if chartutil.getValue(prefix)]
        types = ["· " + t for t in types]
        await ctx.reply(MessageChain([
            Plain(f"c{song.get('idx')} - {song.get('title')}有以下类型WE谱：\n"),
            Plain(f"\n".join(types)),
            Plain(f"\n请指定类型进行查询")
        ]))
        return
    
    weprefix = weprefix[0]
    if chartutil.checkIsHit(chartid, type):
        local_path = os.path.join(CHART_CACHE_DIR, f"we_{chartid}_{type if type else ''}.png")
        try:
            img_conponent = await Image.from_local(local_path)
        except FileNotFoundError:
            await ctx.reply(MessageChain([Plain(f"未找到歌曲对应谱面，可能是内部错误或数据未更新")]))
            return
        diff = chartutil.extractDiff(chartutil.getValue(weprefix))
        await ctx.reply(MessageChain([
            Plain(f"c{song.get('idx')} - {song.get('title')}\n"),
            Plain(f"类型 - {type if type else ''} {'★' * diff}\n"),
            Plain(f"Artist - {song.get('artist')}\n"),
            img_conponent
        ]))
        return
    else:
        print("[ChunithmUtil] 缓存未命中，开始请求")
        asyncio.create_task(chartutil.getChart(chartid, type, weprefix, str(ctx.event.launcher_id), song))