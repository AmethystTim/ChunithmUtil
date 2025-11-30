import os
import json
import re
import dotenv

from pkg.plugin.context import EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import *

from .utils.songutil import SongUtil
from .utils.searcher import Searcher

dotenv.load_dotenv()
SONGS_PATH = os.path.join(os.path.dirname(__file__), "..", os.getenv("SONG_PATH"))
ALIAS_PATH = os.path.join(os.path.dirname(__file__), "..", os.getenv("ALIAS_PATH"))
SEGA_SONG_PATH = os.path.join(os.path.dirname(__file__), "..", os.getenv("SEGA_SONG_PATH"))
COVER_CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'cache', 'covers')

def calcDate(timeStamp: int):
    '''时间戳转YEAR-MONTH-DAY'''
    import time
    timeArray = time.localtime(timeStamp*100)
    return time.strftime("%Y-%m-%d", timeArray)


def searchSong(name: str) -> list[str]:
    '''查询歌曲
    
    Args:
        name: 歌曲名
    Returns:
        cids: 匹配歌曲cid列表
    '''
    songs = []
    cids = []
    
    with open(SONGS_PATH, "r", encoding="utf-8-sig") as f:
        songs = json.load(f)
    with open(ALIAS_PATH, "r", encoding="utf-8") as f:
        alias_for_songs = json.load(f).get("songs")

    # 1. cid搜索
    if re.match(r"^c\d+$", name):
        cid = name[1:]
        if cid.isdigit():
            for song in songs:
                if song.get('idx') == cid and cid not in cids:
                    cids.append(cid)
                    break
        return cids
    
    # 2. 别名搜索 
    for song in alias_for_songs:
        for alias in song.get('aliases'):
            if alias == name.lower():  # 别名采用精准匹配
                cids.append(song.get('cid'))
    if len(cids) > 0:  # 别名存在，直接返回
        return cids
    
    # 3. 模糊搜索
    searcher = Searcher()
    names = list(set([song.get('title') for song in songs]))
    fuzzy_matched_songs = searcher.generalFuzzySearch(name.lower(), names)
    fuzzy_matched_cids = []
    for fuzzy_matched_song in fuzzy_matched_songs:
        for song in songs:
            if song.get('title') == fuzzy_matched_song:
                fuzzy_matched_cids.append(song.get('idx'))
    cids.extend(fuzzy_matched_cids)
    
    cids = list(set(cids))
    return cids
    
async def querySong(ctx: EventContext, args: list) -> None:
    '''回复歌曲查询结果
    
    Args:
        ctx (EventContext): 事件上下文
        args (list): 参数列表
    Returns:
        None: 无返回值
    '''
    name, = args
    songs = []
    
    with open(SONGS_PATH, "r", encoding="utf-8-sig") as f:
        songs = json.load(f)
    
    matched_songs = searchSong(name)
    
    if len(matched_songs) == 1:
        target_songs = [song for song in songs if song.get('idx') == matched_songs[0]]
        song = target_songs[0]
        cid = song.get('idx')
        constants = [str(song.get('const')) for song in target_songs]
        
        songutil = SongUtil()
        songutil.checkIsHit(os.getenv('COVER_URL'), song.get('img'))
        if os.path.exists(os.path.join(COVER_CACHE_DIR, song.get('img') + ".webp")):
            img_conponent = await Image.from_local(os.path.join(COVER_CACHE_DIR, song.get('img') + ".webp"))
        else:
            img_conponent = await Image.from_local(os.path.join(COVER_CACHE_DIR, "default.png"))
        msg_chain = MessageChain([Plain(f"c{cid} - {song.get('title')}\n")]) 
        msg_chain.append(Plain(f"曲师: {song.get('artist')}\n"))
        msg_chain.append(Plain(f"分类：{song.get('genre')}\n"))
        msg_chain.append(Plain(f"BPM: {song.get('bpm')}\n"))
        msg_chain.append(Plain(f"追加版本: {song.get('version')}\n"))
        msg_chain.append(Plain(f"发行日期: {calcDate(song.get('release'))}\n"))
        msg_chain.append(Plain(f"定数: "))
        msg_chain.append(Plain(f"{' / '.join(constants)}\n"))
        msg_chain.append(img_conponent)
        await ctx.reply(msg_chain)
        return
    
    elif len(matched_songs) > 1:
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
    
    else:
        # 尝试搜索sega新曲列表
        sega_songs = []
        with open(SEGA_SONG_PATH, "r", encoding="utf-8") as f:
            sega_songs = json.load(f)
        title_list = [sega_songs.get('title') for sega_songs in sega_songs]
        searcher = Searcher()
        matched_songs = searcher.generalFuzzySearch(name, title_list)
        
        if len(matched_songs) == 1:
            matched_song = [song for song in sega_songs if song.get('title') == matched_songs[0]][0]
            
            songutil = SongUtil()
            songutil.checkIsHit(os.getenv('SEGA_COVER_URL'), matched_song.get('image'))
            
            img = await Image.from_local(os.path.join(COVER_CACHE_DIR, matched_song.get('image')))
            await ctx.reply(MessageChain([
                Plain(f"新曲 - {matched_song.get('title')}\n"),
                Plain(f"by {matched_song.get('artist')}\n"),
                Plain(f"Basic {matched_song.get('lev_bas')}\n"),
                Plain(f"Advanced {matched_song.get('lev_adv')}\n"),
                Plain(f"Expert {matched_song.get('lev_exp')}\n"),
                Plain(f"Master {matched_song.get('lev_mas')}\n"),
                Plain(f"Ultima {matched_song.get('lev_ult', '-')}" if matched_song.get('lev_ult')!="" else ""),
                img,
            ]))
            return
        elif len(matched_songs) > 1:
            return
        else:
            await ctx.reply(MessageChain([Plain("没有找到该歌曲，试着输入歌曲全称或其他别名")]))
            return