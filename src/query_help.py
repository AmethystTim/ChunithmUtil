from pkg.plugin.context import EventContext
from pkg.platform.types import *

async def queryHelp(ctx: EventContext) -> None:
    '''获取帮助信息
    
    Args:
        ctx (EventContext): 事件上下文
    Returns:
        None
    '''
    await ctx.reply(MessageChain([
        Plain("chu help - 查看帮助"),
        Plain("[别名]是什么歌 - 别名查找歌曲"),
        Plain("chu查歌 [歌曲全名/cid] - 精准查找歌曲"),
        Plain("alias [歌曲cid] [别名1，别名2，...] - 为歌曲添加别名"),
        Plain("别名 [歌曲cid] - 查看指定歌曲所有别名"),
        Plain("chu随机一曲 - 随机一首歌"),
        Plain("chu lv [定数] - 查看指定定数所有歌曲"), 
        Plain("chu 容错 [歌曲cid/别名] [难度] - 容错计算"),
        Plain("chuchart [歌曲cid/别名] [难度] - 查看谱面"),
        Plain("chu曲师 [曲师名] - 查看曲师作品"),
        Plain("chu谱师 [谱师名] - 查看谱师谱面"),
    ]))