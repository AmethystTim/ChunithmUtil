import os
import dotenv
import subprocess
import json

from pkg.plugin.context import EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import *

from .utils import songmeta

dotenv.load_dotenv()
SCRIPT_SONGMETA_PATH = os.path.join(os.path.dirname(__file__), "utils", "songmeta.py")
SCRIPT_MAPPING_PATH = os.path.join(os.path.dirname(__file__), "utils", "mapping.py")

async def queryUpdate(ctx: EventContext, args: list) -> None:
    _ = args
    
    diff = None
    try:
        diff = songmeta.songMeta()
        subprocess.run(['python', SCRIPT_MAPPING_PATH])
        msg_chain = MessageChain([
            Plain("更新成功"),
        ])
        
        if len(diff) > 20:
            msg_chain.append(Plain(f"，新增曲目过多，仅展示前20首"))
        if len(diff) != 0:
            msg_chain.append(Plain(f"，新增曲目：\n"))
            for song in diff[::-1][ : min(20, len(diff))]:
                msg_chain.append(Plain(f"· {song.get('songId')}\n"))
        await ctx.reply(msg_chain)
    
    except subprocess.CalledProcessError as e:
        await ctx.reply(MessageChain([Plain(f"更新失败：{e}")]))
        return