import os
import json
import re
import dotenv

from pkg.plugin.context import EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import *

from .utils.songutil import SongUtil
from .utils.aliaslogger import AliasLogger
from .query_song import searchSong

dotenv.load_dotenv()
SONGS_PATH = os.path.join(os.path.dirname(__file__), "..", os.getenv("SONG_PATH"))
ALIAS_PATH = os.path.join(os.path.dirname(__file__), "..", os.getenv("ALIAS_PATH"))

async def queryAddAlias(ctx: EventContext, args: list) -> None:
    '''添加别名
    
    Args:
        ctx (EventContext): 事件上下文
        args (list): 参数列表
    Returns:
        None: 无返回值
    '''
    id, aliases_to_add = args
    
    aliases_to_add = re.split(r"[，,]", aliases_to_add)
    if not re.match(r"^c\d+$", id):
        await ctx.reply(MessageChain([Plain("请使用cid进行别名添加")]))
        return
    matched_songs = searchSong(id)
    if len(matched_songs) == 0:
        await ctx.reply(MessageChain([Plain("未找到cid对应的歌曲，请检查cid是否正确")]))
        return
    elif len(matched_songs) > 1:
        songs = []
        with open(SONGS_PATH, 'r', encoding='utf-8') as f:
            songs = json.load(f).get('songs')
        msg_chain = MessageChain([Plain(f"有多个曲目符合条件\n")])
        for songId in matched_songs:
            song_index = songs.index([song for song in songs if song.get('songId') == songId][0])
            msg_chain.append(Plain(f"c{song_index} - {songId}\n"))
        msg_chain.append(Plain(f"\n请使用cid进行精准查询"))
        await ctx.reply(msg_chain)
        return
    songId = matched_songs[0]
    songs = []
    with open(SONGS_PATH, 'r', encoding='utf-8') as f:
        songs = json.load(f).get('songs')
    song_index = songs.index([song for song in songs if song.get('songId') == songId][0])
    
    alias_json_songs = []
    with open(ALIAS_PATH, 'r', encoding='utf-8') as f:
        alias_json_songs = json.load(f).get('songs')
    
    songutil = SongUtil()
    valid_aliases, invalid_aliases = songutil.addAlias(songId, alias_json_songs, aliases_to_add)
    
    '''记录别名添加日志'''
    aliaslogger = AliasLogger()
    aliaslogger.log({
        "user_id": ctx.event.sender_id,
        "user_name": ctx.event.query.message_event.sender.get_name(),
        "group_id": ctx.event.launcher_id,
        "cid": f"c{song_index}",
        "songId": songId,
        "valid_aliases": valid_aliases,
        "invalid_aliases": invalid_aliases
    })
    
    await ctx.reply(MessageChain([
        Plain(f"歌曲{songId}的别名：{', '.join(valid_aliases)}添加成功\n")
        if len(valid_aliases) > 0 else Plain(""),
        Plain(f"歌曲{songId}的别名：{', '.join(invalid_aliases)}已存在")
        if len(invalid_aliases) > 0 else Plain(""),
        Plain("\n添加歌曲别名将记录在日志中")
    ]))

async def queryGetAlias(ctx: EventContext, args: list) -> None:
    '''获取曲目别名
    
    Args:
        ctx (EventContext): 事件上下文
        args (list): 参数列表
    Returns:
        None: 无返回值
    '''
    id, = args
    
    matched_songs = searchSong(id)
    songs = []
    with open(SONGS_PATH, 'r', encoding='utf-8') as f:
        songs = json.load(f).get('songs')
    if len(matched_songs) == 0:
        await ctx.reply(MessageChain([Plain("未找到该歌曲，试着输入歌曲全称或其他别名")]))
        return
    elif len(matched_songs) > 1:
        msg_chain = MessageChain([Plain(f"有多个曲目符合条件\n")])
        for songId in matched_songs:
            song_index = songs.index([song for song in songs if song.get('songId') == songId][0])
            msg_chain.append(Plain(f"c{song_index} - {songId}\n"))
        msg_chain.append(Plain(f"\n请使用cid进行精准查询"))
        await ctx.reply(msg_chain)
        return
    
    songId = matched_songs[0]
    song_index = songs.index([song for song in songs if song.get('songId') == songId][0])
    
    alias_json_songs = []
    with open(ALIAS_PATH, 'r', encoding='utf-8') as f:
        alias_json_songs = json.load(f).get('songs')
    
    songutil = SongUtil()
    aliases = songutil.getAlias(songId, alias_json_songs)
    if len(aliases) == 0:
        await ctx.reply(MessageChain([Plain(f"c{song_index} - {songId}暂无别名")]))
        return
    
    msg_chain = MessageChain([Plain(f"c{song_index} - {songId}的别名：")])
    for alias in aliases:
        msg_chain.append(Plain(f"\n· {alias}"))
    msg_chain.append(Plain(f"\n别名均为用户添加，与BOT无关"))
    await ctx.reply(msg_chain)

async def queryDelAlias(ctx: EventContext, args: list) -> None:
    pass
