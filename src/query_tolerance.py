import os
import json
import dotenv

from pkg.plugin.context import EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import *

from .query_song import searchSong
from .utils.songutil import SongUtil

dotenv.load_dotenv()
SONGS_PATH = os.path.join(os.path.dirname(__file__), "..", os.getenv("SONG_PATH"))

async def queryTolerance(ctx: EventContext, args: list) -> None:
    '''计算指定歌曲难度容错
    
    Args:
        ctx (EventContext): 事件上下文
        msg (str): 指令内容
    Returns:
        None: 无返回值
    '''
    name, difficulty = args
    
    songs = []
    song = None
    with open(SONGS_PATH, "r", encoding="utf-8-sig") as file:
        songs = json.load(file)
    
    if difficulty == None:  # 默认mas
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
    
    tolerance = songutil.calcTolerance(song, difficulty)
    await ctx.reply(MessageChain([
        Plain(f'c{cid} - {song.get("title")}\n难度 - {difficulty}\n'),
        Plain(f'· 鸟容错\n{tolerance["1007500"]["attack"]}个attack + {tolerance["1007500"]["justice"]}个小j\n'),
        Plain(f'· 鸟加容错\n{tolerance["1009000"]["attack"]}个attack + {tolerance["1009000"]["justice"]}个小j')
    ]))