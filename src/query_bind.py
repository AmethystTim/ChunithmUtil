import asyncio
import os
import os.path as osp
import json
import dotenv
import requests

from pkg.plugin.context import EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import *

from .utils.songutil import *
from .utils.apicaller import *

dotenv.load_dotenv()
SONGS_PATH = os.path.join(os.path.dirname(__file__), "..", os.getenv("SONG_PATH"))
LX_JSON_PATH = osp.join(osp.dirname(__file__), '..', 'data', 'lx.json')
LX_RECORD_URL = 'https://maimai.lxns.net/api/v0/user/chunithm/player/scores'
RIN_JSON_PATH = osp.join(osp.dirname(__file__), '..', 'data', 'rin.json')
SHIRO_JSON_PATH = osp.join(osp.dirname(__file__), '..', 'data','shiro.json')

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
        token = token.strip()
        try:
            response = await asyncio.to_thread(
                requests.get,
                LX_RECORD_URL,
                headers={'X-User-Token': token},
                timeout=15,
            )
        except requests.RequestException:
            await self.ctx.reply([Plain('验证落雪个人 API 密钥失败：连接查分器时出错，请稍后重试')])
            return

        try:
            result = response.json()
        except ValueError:
            await self.ctx.reply([Plain('验证落雪个人 API 密钥失败：查分器返回了无效响应，请稍后重试')])
            return
        if not isinstance(result, dict):
            await self.ctx.reply([Plain('验证落雪个人 API 密钥失败：查分器返回了无效响应，请稍后重试')])
            return
        if response.status_code == 401 or result.get('code') == 401:
            await self.ctx.reply([Plain('落雪个人 API 密钥无效或已过期，绑定未修改。请从账号详情复制完整的新密钥')])
            return
        if response.status_code != 200 or result.get('code') != 200 or result.get('success') is False:
            await self.ctx.reply([Plain(f'验证落雪个人 API 密钥失败（HTTP {response.status_code}），绑定未修改')])
            return

        users = await self.readUsersJson()
        was_bound = self.checkIsBind(users)
        users[self.user_id] = token
        if await self.writeUsersJson(users) != 0:
            return
        message = '已将原TOKEN替换为新TOKEN，请及时撤回个人TOKEN' if was_bound else '绑定成功，请及时撤回个人TOKEN'
        await self.ctx.reply([Plain(message)])

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

class ShiroQueryBind(RinQueryBind):
    async def readUsersJson(self):
        users = {}
        with open(SHIRO_JSON_PATH, 'r') as f:
            users = json.load(f).get('users', {})
        return users

    async def writeUsersJson(self, users: dict):
        try:
            with open(SHIRO_JSON_PATH, 'w') as f:
                json.dump({'users': users}, f, indent=4)
            return 0
        except Exception as e:
            await self.ctx.reply([Plain(f'写入失败：{e}')])
            return -1

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
        case 'shiro':
            if token is None:
                await ctx.reply(MessageChain([Plain(f"请输入{server}服务器的卡号")]))
                return
            shqb = ShiroQueryBind(ctx)
            await shqb.bindAccount(token)
        case _:
            await ctx.reply(MessageChain([Plain(f"未知服务器{server}")]))
            return