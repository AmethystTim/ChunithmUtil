import os
import os.path as osp
import json
import dotenv

from pkg.plugin.context import EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import *
from plugins.ChunithmUtil.src.query_copy import RIN_JSON_PATH

from .utils.songutil import *
from .utils.apicaller import *

dotenv.load_dotenv()
SONGS_PATH = os.path.join(os.path.dirname(__file__), "..", os.getenv("SONG_PATH"))
LX_JSON_PATH = osp.join(osp.dirname(__file__), '..', 'data', 'lx.json')
RIN_JSON_PATH = osp.join(osp.dirname(__file__), '..', 'data', 'rin.json')

class LXQueryBind():
    def __init__(self, ctx: EventContext):
        self.ctx = ctx
        self.user_id = str(ctx.event.sender_id)
        
    async def readUsersJson(self):
        users = {}
        with open(LX_JSON_PATH, 'r') as f:
            users = json.load(f).get('users', {})
        return users
    
    def checkIsBind(self, users: dict):
        return self.user_id in users.keys()
    
    async def writeUsersJson(self, users: dict):
        try:
            with open(LX_JSON_PATH, 'w') as f:
                json.dump({'users': users}, f, indent=4)
            return 0
        except Exception as e:
            await self.ctx.reply([Plain(f'写入失败：{e}')])
            return -1
    
    async def bindAccount(self, token: str):
        users = await self.readUsersJson()
        # 检查是否已绑定
        if self.checkIsBind(users):
            users[self.user_id] = token
            await self.writeUsersJson(users)
            await self.ctx.reply([Plain('已将原TOKEN替换为新TOKEN，请及时撤回个人TOKEN')])
            return
        # 绑定账号
        users[self.user_id] = token
        await self.writeUsersJson(users)
        await self.ctx.reply([Plain('绑定成功，请及时撤回个人TOKEN')])

class RinQueryBind():
    def __init__(self, ctx: EventContext):
        self.ctx = ctx
        self.user_id = str(ctx.event.sender_id)
        
    async def readUsersJson(self):
        users = {}
        with open(RIN_JSON_PATH, 'r') as f:
            users = json.load(f).get('users', {})
        return users
    
    def checkIsBind(self, users: dict):
        return self.user_id in users.keys()
    
    async def writeUsersJson(self, users: dict):
        try:
            with open(RIN_JSON_PATH, 'w') as f:
                json.dump({'users': users}, f, indent=4)
            return 0
        except Exception as e:
            await self.ctx.reply([Plain(f'写入失败：{e}')])
            return -1
    
    async def bindAccount(self, token: str):
        users = await self.readUsersJson()
        # 检查是否已绑定
        if self.checkIsBind(users):
            users[self.user_id] = token
            await self.writeUsersJson(users)
            await self.ctx.reply([Plain('已将原卡号替换为新卡号，请及时撤回个人卡号')])
            return
        # 绑定账号
        users[self.user_id] = token
        await self.writeUsersJson(users)
        await self.ctx.reply([Plain('绑定成功，请及时撤回个人卡号')])

async def queryBind(ctx: EventContext, args: list, **kwargs) -> None:
    '''绑定'''
    server, token = args
    match server:
        case 'lx':
            if token is None:
                await ctx.reply(MessageChain([Plain(f"请输入{server}服务器的token")]))
                return
            lqb = LXQueryBind(ctx)
            await lqb.bindAccount(token)
        case 'rin':
            if token is None:
                await ctx.reply(MessageChain([Plain(f"请输入{server}服务器的卡号")]))
                return
            rqb = RinQueryBind(ctx)
            await rqb.bindAccount(token)
        case _:
            await ctx.reply(MessageChain([Plain(f"未知服务器{server}")]))
            return