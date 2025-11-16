import os
import json
import dotenv
import asyncio

from pkg.plugin.context import EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import *

from .query_song import searchSong
from .utils.songutil import SongUtil
from .utils.chartutil import ChartUtil

dotenv.load_dotenv()
SONGS_PATH = os.path.join(os.path.dirname(__file__), "..", os.getenv("SONG_PATH"))
CHART_CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'cache', 'charts')

async def queryChart(ctx: EventContext, args: list) -> None:
    '''查询谱面
    
    
    Args:
        ctx (EventContext): 事件上下文
        args (list): 参数列表
    Returns:
        None: 无返回值
    '''
    songs = []
    song = {}
    name, difficulty = args
    
    with open(SONGS_PATH, "r", encoding="utf-8-sig") as file:
        songs = json.load(file)
    
    if difficulty == None:
        difficulty = "mas"
    
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
    
    songutil = SongUtil()
    index = songutil.getDiff2Index(difficulty)
    try:
        if index == 4 and len(target_songs) < 5: # 检查是否有Ultima难度
            await ctx.reply(MessageChain([Plain(f"歌曲{song.get('title')}无Ultima难度")]))
            return
    except Exception as e:
        await ctx.reply(MessageChain([Plain(f"未知难度")]))
        return
    # 切换为对应难度
    song = target_songs[index]

    chartutil = ChartUtil()
    chartid = chartutil.getChartID(song)
    if chartid == None:
        await ctx.reply(MessageChain([Plain(f"未找到歌曲对应谱面，可能是内部错误或数据未更新")]))
        return
    if chartutil.checkIsHit(chartid, difficulty):
        local_path = os.path.join(CHART_CACHE_DIR, f"{chartid}_{'' if difficulty == 'mas' else difficulty}.png")
        try:
            img_conponent = await Image.from_local(local_path)
        except FileNotFoundError:
            await ctx.reply(MessageChain([Plain(f"未找到歌曲对应谱面，可能是内部错误或数据未更新")]))
            return
        await ctx.reply(MessageChain([
            Plain(f"c{cid} - {song.get('title')}\n"),
            Plain(f"难度 - {difficulty}\n"),
            Plain(f"Artist - {song.get('artist')}\n"),
            Plain(f"BPM - {song.get('bpm')}\n"),
            Plain(f"Notes - {song.get('notes')}"),
            img_conponent
        ]))
        return
    else:
        print("[ChunithmUtil] 缓存未命中，开始请求")
        asyncio.create_task(chartutil.getChart(chartid, difficulty, str(ctx.event.launcher_id), song))