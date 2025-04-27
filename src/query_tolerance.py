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
    song_name, difficulty = args
    
    songs = []
    
    with open(SONGS_PATH, "r", encoding="utf-8") as file:
        songs = json.load(file).get("songs")
    
    if difficulty == None:  # 默认mas
        difficulty = "mas"

    matched_songs = searchSong(ctx, song_name)
    
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
        msg_chain.append(Plain(f"\n请使用“chu容错 [cid]”进行容错计算"))
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
    
    tolerance = songutil.calcTolerance(song['sheets'][index])
    await ctx.reply(MessageChain([
        Plain(f'歌曲 - {song.get("songId")} - {difficulty}难度容错：\n'),
        Plain(f'鸟容错\n100小j：{tolerance["1007500"]["100j"]}个attack\n50小j：{tolerance["1007500"]["50j"]}个attack\n'),
        Plain(f'鸟加容错\n100小j：{tolerance["1009000"]["100j"]}个attack\n50小j：{tolerance["1009000"]["50j"]}个attack')
    ]))