import os
import json
import dotenv
from itertools import islice

from pkg.plugin.context import EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import *

from .utils.searcher import Searcher
from .utils.songutil import SongUtil

dotenv.load_dotenv()
SONGS_PATH = os.path.join(os.path.dirname(__file__), "..", os.getenv("SONG_PATH"))

async def queryNoteDesigner(ctx: EventContext, args: list) -> None:
    '''查询谱师
    
    Args:
        ctx (EventContext): 事件上下文
        args (list): 参数列表
    Returns:
        None
    '''
    songs = []  # 歌曲列表
    matched_note_designers = [] # 匹配到的谱师列表
    target_note_designer, = args
    
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.getenv("SONG_PATH")), "r", encoding="utf-8") as file:
        songs = json.load(file).get("songs")
    
    searcher = Searcher()
    songutil = SongUtil()
    
    matched_note_designers = searcher.generalFuzzySearch(target_note_designer, songutil.getNoteDesigners(songs))
    
    if len(matched_note_designers) == 0:
        await ctx.reply(MessageChain([Plain(f"没有找到{target_note_designer}，请尝试输入谱师全称")]))
        return
    
    elif len(matched_note_designers) == 1:
        note_designer_name = matched_note_designers[0]
        sheets_by_note_designer = songutil.getSheetsByNoteDesigner(note_designer_name, songs)
        msg_chain = MessageChain([Plain(f"谱师 - {note_designer_name}谱面列表：\n")])
        if len(sheets_by_note_designer) > 20:
            await ctx.reply(MessageChain([Plain(f"谱面过多，仅展示前20首歌曲")]))
        for songId, difficulties in islice(sheets_by_note_designer.items(), min(len(sheets_by_note_designer), 20)):
            msg_chain.append(Plain(f"· {songId}\n\t"))
            msg_chain.append(Plain("-".join(difficulties)))
            msg_chain.append(Plain("\n"))
        await ctx.reply(msg_chain)
    
    else:
        msg_chain = MessageChain([Plain(f"有多个谱师符合条件\n")])
        for note_designer in matched_note_designers:
            msg_chain.append(Plain(f"· {note_designer}\n"))
        msg_chain.append(Plain(f"\n请使用“chu谱师 [谱师全名]”进行查询"))
        await ctx.reply(msg_chain)
    return