import os
import json
import dotenv

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
    song_name, difficulty = args
    
    with open(SONGS_PATH, "r", encoding="utf-8") as file:
        songs = json.load(file).get("songs")
    
    if difficulty == None:
        difficulty = "mas"
    
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
    
    songutil = SongUtil()
    index = songutil.getDiff2Index(difficulty)
    try:
        if index == 4 and len(song['sheets']) < 5: # 检查是否有Ultima难度
            await ctx.reply(MessageChain([Plain(f"歌曲{song_name}无Ultima难度")]))
            return
    except Exception as e:
        await ctx.reply(MessageChain([Plain(f"未知难度")]))
        return

    chartutil = ChartUtil()
    chartid = chartutil.getChartID(song)
    chartutil.checkIsHit(chartid, difficulty)
    
    local_path = os.path.join(CHART_CACHE_DIR, f"{chartid}_{'' if difficulty == 'mas' else difficulty}.png")
    try:
        img_conponent = await Image.from_local(local_path)
    except FileNotFoundError:
        await ctx.reply(MessageChain([Plain(f"未找到歌曲对应谱面，可能是内部错误或数据未更新")]))
        return
    await ctx.reply(MessageChain([
        Plain(f"歌曲 - {song.get('songId')}\n"),
        Plain(f"难度 - {difficulty}\n"),
        Plain(f"Artist - {song.get('artist')}\n"),
        Plain(f"NoteDesigner - {song.get('sheets')[index]['noteDesigner']}\n"),
        Plain(f"BPM - {song.get('bpm')}\n"),
        Plain(f"Notes - {song.get('sheets')[index]['noteCounts']['total']}"),
        img_conponent
    ]))
    return
       