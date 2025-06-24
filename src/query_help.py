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
        Plain("CHUNITHM UTILS 指令帮助：\n"),
        Plain("· chu help - 查看帮助\n"),
        Plain("· [别名/cid]是什么歌 - 查找歌曲\n"),
        Plain("· chuset [歌曲cid] [别名1，别名2，...] - 为歌曲添加别名\n"),
        Plain("· 别名 [歌曲cid] - 查看指定歌曲所有别名\n"),
        Plain("· chu随机一曲 - 随机一首歌\n"),
        Plain("· chu lv [定数] - 查看指定定数所有歌曲\n"), 
        Plain("· chu容错 [歌曲cid/别名] [难度] - 容错计算\n"),
        Plain("· chuchart [歌曲cid/别名] [难度] - 查看谱面\n"),
        Plain("· chu曲师 [曲师名] - 查看曲师作品\n"),
        Plain("· chu谱师 [谱师名] - 查看谱师谱面\n"),
        Plain("· chu update - 更新曲目、谱面信息\n"),
        Plain("· chu guess [难度] - 创建猜歌游戏\n"),
        Plain("· chu guess end - 结束当前猜歌游戏\n"),
        Plain("· chu hint - 请求猜歌提示\n"),
        Plain("· guess [歌曲名] - 猜歌\n"),
    ]))