import os
import json
import random

from pkg.plugin.context import EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import *

from .utils.songutil import SongUtil

COVER_CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'cache', 'covers')

async def queryRdnSong(ctx: EventContext, args: list) -> None:
    '''随机一曲
    
    Args:
        ctx (EventContext): 事件上下文
        args (list): 参数列表
    Returns:
        None: 无返回值
    '''
    
    songs = []
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.getenv("SONG_PATH")), "r", encoding="utf-8") as file:
        songs = json.load(file).get("songs")
        
    song = random.choice(songs)
    
    songutil = SongUtil()
    songutil.checkIsHit(os.getenv('COVER_URL'), song.get('imageName'))
    img_conponent = await Image.from_local(os.path.join(COVER_CACHE_DIR, song.get('imageName')))
    msg_chain = MessageChain([Plain(f"{song.get('title')}\nby {song.get('artist')}")])
    for sheet in song.get('sheets'):
        msg_chain.append(Plain(f"\n{str(sheet.get('difficulty')).capitalize()} {sheet.get('internalLevelValue')}"))
    msg_chain.append(img_conponent)
    await ctx.reply(msg_chain)