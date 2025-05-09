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

def searchSong(song_name: str) -> list[str]:
    '''查询歌曲
    
    Args:
        song_name: 歌曲名
    Returns:
        matched_songs: 匹配歌曲songId列表
    '''
    songs = []
    matched_songs = []
    
    with open(SONGS_PATH, "r", encoding="utf-8") as f:
        songs = json.load(f).get("songs")
    with open(ALIAS_PATH, "r", encoding="utf-8") as f:
        alias_json_songs = json.load(f).get("songs")

    # 1. cid搜索
    if re.match(r"^c\d+$", song_name):
        song_index = int(song_name[1:])
        if not (0 <= song_index < len(songs)):
            return []
        song = songs[song_index]
        matched_songs.append(song.get('songId'))
        return matched_songs
    
    # 2.1 别名搜索 
    for song in alias_json_songs:
        for alias in song.get('aliases'):
            if alias == song_name:  # 别名采用精准匹配
                matched_songs.append(song.get('songId'))
    
    # 2.2 模糊搜索
    searcher = Searcher()
    songId_list = [song.get('songId') for song in songs]
    fuzzy_searchresult = searcher.generalFuzzySearch(song_name, songId_list)
    matched_songs.extend(fuzzy_searchresult)
    
    matched_songs = list(set(matched_songs))
    return matched_songs
    
async def querySong(ctx: EventContext, args: list) -> None:
    '''回复歌曲查询结果
    
    Args:
        ctx (EventContext): 事件上下文
        args (list): 参数列表
    Returns:
        None: 无返回值
    '''
    song_name, = args
    songs = []
    
    with open(SONGS_PATH, "r", encoding="utf-8") as f:
        songs = json.load(f).get("songs")
    
    matched_songs = searchSong(song_name)
    
    if len(matched_songs) == 1:
        song = [song for song in songs if song.get('songId') == matched_songs[0]][0]
        song_index = songs.index(song)
        
        songutil = SongUtil()
        songutil.checkIsHit(os.getenv('COVER_URL'), song.get('imageName'))
        
        img_conponent = await Image.from_local(os.path.join(COVER_CACHE_DIR, song.get('imageName')))
        msg_chain = MessageChain([Plain(f"c{song_index} - {song.get('title')}\n")]) 
        msg_chain.append(Plain(f"曲师: {song.get('artist')}\n"))
        msg_chain.append(Plain(f"分类：{song.get('category')}\n"))
        msg_chain.append(Plain(f"追加版本: {song.get('version')}\n"))
        msg_chain.append(Plain(f"发行日期: {song.get('releaseDate')}\n"))
        msg_chain.append(Plain(f"定数: "))
        rating_list = [str(sheet.get('internalLevelValue')) for sheet in song.get('sheets')]
        msg_chain.append(Plain(f"{' / '.join(rating_list)}\n"))
        msg_chain.append(img_conponent)
        await ctx.reply(msg_chain)
        return
    
    elif len(matched_songs) > 1:
        msg_chain = MessageChain([Plain(f"有多个曲目符合条件\n")])
        for songId in matched_songs:
            song_index = songs.index([song for song in songs if song.get('songId') == songId][0])
            msg_chain.append(Plain(f"c{song_index} - {songId}\n"))
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
        matched_songs = searcher.generalFuzzySearch(song_name, title_list)
        
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