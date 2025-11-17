import os
import json
import dotenv

from pkg.plugin.context import EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import *

from .utils.searcher import Searcher
from .utils.songutil import SongUtil

dotenv.load_dotenv()
SONGS_PATH = os.path.join(os.path.dirname(__file__), "..", os.getenv("SONG_PATH"))

async def queryArtist(ctx: EventContext, args: list) -> None:
    '''查询曲师所有作品
    
    Args:
        ctx (EventContext): 事件上下文
        args (list): 参数列表
    Returns:
        None: 无返回值
    '''
    target_artist, = args
    
    songs = []
    matched_artists = []
    
    with open(SONGS_PATH, "r", encoding="utf-8-sig") as file:
        songs = json.load(file)
    
    searcher = Searcher()
    songutil = SongUtil()
    
    matched_artists = searcher.generalFuzzySearch(target_artist, songutil.getArtists(songs))
    
    if len(matched_artists) == 0:
        await ctx.reply(MessageChain([Plain(f"没有找到{target_artist}，请尝试输入曲师全称")]))
        return
    
    elif len(matched_artists) == 1:
        artist_name = matched_artists[0]
        songs_by_artist = songutil.getSongsByArtist(artist_name, songs)
        msg_chain = MessageChain([Plain(f"曲师 - {artist_name}作品列表：\n")])
        for song in songs_by_artist:
            msg_chain.append(Plain(f"· c{song.get('idx')} - {song.get('title')}\n"))
        await ctx.reply(msg_chain)
    
    else:
        msg_chain = MessageChain([Plain(f"有多个曲师符合条件\n")])
        for artist in matched_artists:
            msg_chain.append(Plain(f"· {artist}\n"))
        msg_chain.append(Plain(f"\n请使用“chu曲师 [曲师全名]”进行查询"))
        await ctx.reply(msg_chain)
    return