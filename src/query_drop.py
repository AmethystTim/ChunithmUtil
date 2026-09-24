import os.path as osp
import sqlite3
from contextlib import closing

from pkg.plugin.context import EventContext
from pkg.platform.types import MessageChain, Plain

DB_PATH = osp.join(osp.dirname(__file__), '..', 'data', 'data.db')


async def queryDrop(ctx: EventContext) -> None:
    """清除消息发送者自己的游玩记录。"""
    user_id = str(ctx.event.sender_id)
    try:
        with closing(sqlite3.connect(DB_PATH)) as conn:
            with conn:
                cursor = conn.execute("DELETE FROM record WHERE user_id = ?", (user_id,))
                deleted = cursor.rowcount
    except sqlite3.Error as e:
        print(f"清除游玩记录失败：{e}")
        await ctx.reply(MessageChain([Plain("清除游玩记录失败，请稍后重试")]))
        return

    if deleted:
        message = f"已清除你的全部游玩记录，共{deleted}条"
    else:
        message = "你还没有游玩记录，无需清除"
    await ctx.reply(MessageChain([Plain(message)]))
