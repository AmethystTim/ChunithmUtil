import os
import json
import dotenv
import sqlite3

from pkg.plugin.context import EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import *

from .query_song import searchSong
from .utils.songutil import SongUtil

dotenv.load_dotenv()
SONGS_PATH = os.path.join(os.path.dirname(__file__), "..", os.getenv("SONG_PATH"))
DB_PATH = os.path.join(os.path.dirname(__file__), "..", 'data', 'data.db')

def updateScore(user_id: str, cid: str, score: int, difficulty: int, name: str) -> None:
    '''更新歌曲分数'''
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(f"INSERT OR REPLACE INTO record (user_id, cid, score, difficulty) VALUES (?, ?,?,?)", (user_id, cid, score, difficulty))
        conn.commit()
        conn.close()
        su = SongUtil()
        return 0, f"已将c{cid} - {name}的{su.getIndex2Diff(difficulty)}难度分数更新为{score}"
    except sqlite3.Error as e:
        print(e)
        return -1, f"更新失败：{e}"
    

async def queryUpdScore(ctx: EventContext, args: list) -> None:
    '''更新歌曲分数
    
    Args:
        ctx (EventContext): 事件上下文
        args (list): 参数列表
    Returns:
        None: 无返回值
    '''
    score, name, difficulty = args
    score = int(score)
    name = name.strip()
    user_id = str(ctx.event.sender_id)
    if difficulty is None:
        difficulty = "mas"
    cids = searchSong(name)
    
    songs = []
    with open(SONGS_PATH, 'r', encoding='utf-8-sig') as f:
        songs = json.load(f)
    if len(cids) == 0:
        await ctx.reply(MessageChain([Plain("没有找到该歌曲，试着输入歌曲全称或其他别名")]))
        return
    elif len(cids) > 1:
        msg_chain = MessageChain([Plain(f"有多个曲目符合条件\n")])
        for cid in cids:
            name = None
            for song in songs:
                if song.get('idx') == cid:
                    name = song.get('title')
                    break
            msg_chain.append(Plain(f"c{cid} - {name}\n"))
        msg_chain.append(Plain(f"\n请使用cid进行精准查询"))
        await ctx.reply(msg_chain)
        return
    
    cid = cids[0]
    target_songs = []
    songutil = SongUtil()
    difficulty = songutil.getDiff2Index(difficulty)
    for song in songs:
        if song.get('idx') == cid:
            target_songs.append(song)
    try:
        if difficulty == 4 and len(target_songs) < 5: # 检查是否有Ultima难度
            await ctx.reply(MessageChain([Plain(f"歌曲{song.get('title')}无Ultima难度")]))
            return
    except Exception as e:
        await ctx.reply(MessageChain([Plain(f"未知难度： {e}")]))
        return
    # 切换为对应难度
    song = target_songs[difficulty]

    _, msg = updateScore(user_id, cid, score, difficulty, song.get('title'))
    msg_chain = MessageChain([Plain(f"{msg}")])
    await ctx.reply(msg_chain)
    