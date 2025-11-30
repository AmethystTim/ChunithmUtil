import re
import os
import dotenv

from pkg.plugin.context import register, handler, BasePlugin, APIHost, EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import *

from .src.query_help import *
from .src.query_song import *
from .src.query_chart import *
from .src.query_alias import *
from .src.query_rdnsong import *
from .src.query_tolerance import * 
from .src.query_aritst import *
# from .src.query_notedesigner import *
from .src.query_level import *
from .src.query_update import *
from .src.query_guess import *
from .src.query_method import *
from .src.query_wechart import *
from .src.query_updscore import *
from .src.query_querybest import *
from .src.query_copy import *
from .src.query_bind import *

from .src.utils.argsparser import *
from .src.utils.guessgame import *

os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("all_proxy", None)
os.environ.pop("ALL_PROXY", None)

# 注册插件
@register(name="ChunithmUtil", description="集成多项Chunithm实用功能的LangBot插件🧩", version="1.1", author="Amethyst")
class ChunithmUtilPlugin(BasePlugin):
    # 插件加载时触发
    def __init__(self, host: APIHost):
        self.instructions = {
            "chu help": 
                r"^chu\s?help$",
            # ===== 查歌 =====
            "[歌名]是什么歌": 
                r"^(.+)是什么歌$",
            "chu随机一曲": 
                r"^chu随机[一曲]*$",
            "添加别名|chuset [歌曲id] [别名1],[别名2],...": 
                r"(?:^添加别名|chuset) (c\d+)\s+((?:[^,，]+[,，]?)+)$",
            "别名[歌曲id|歌曲别名]": 
                r"^别名\s*(.+)$",
            "chu lv [难度]": 
                r"^chu\s?lv\s?(\S+)$",
            "chu容错 [歌曲id/别名] [难度]": 
                r"^(?:chu容错|churc)\s?(c\d+|.+?)(?: (exp|mas|ult))?$",
            # ===== 查谱 =====
            "chuchart [歌曲id/别名] [难度]": 
                r"^chuchart\s?(c\d+|.+?)(?: (exp|mas|ult))?$",
            "wechart [歌曲id/别名] [难度]":
                r"^wechart\s?(c\d+|.+?)(?=\s+[^\s]$|$)(?:\s+([^\s]))?$",
            # ===== 查人 =====
            "chu曲师 [曲师名]" : 
                r"^chu(?:曲师|\s?qs)\s?(.+)$",
            # "chu谱师 [谱师名]": 
            #     r"^chu(?:谱师|\s?ps)\s?(.+)$",
            "chu update":
                r"^chu\s?update$",
            # ===== 猜歌 =====
            "chu guess [难度]":
                r"^chu\s?guess(?: (bas|adv|exp|mas|ult))?$",
            "chu guess end":
                r"^(chu\s?guess\s?end|cge)$",
            "guess [歌名]":
                r"^guess\s?(.+)$",
            "chu hint":
                r"^chu\s?hint$",
            # ===== 查分 =====
            "update [分数] [歌名] [难度]":
                 r"upd\s*(\d+)\s*(.*?)(?:\s+(exp|mas|ult))?$",
            "b30":
                r"^b30(?:\s?(simple))?$",
            "b50":
                r"^b50(?:\s?(simple))?$",
            "chu copy [服务器]":
                r"^chu\s?copy\s?(\S+)$",
            "chu bind [服务器] [TOKEN]":
                r"^chu\s*bind\s+(\S+)\s+(\S+)$",
            # ===== 弃用 =====
            "[歌名]这里怎么打":
                r"^(.+)这里怎么打$",
            "[歌名]有什么手法":
                r"^(.+)有什么手法$",
            "[歌名]的[mid]这么打":
                r"^(.+)的(\S+)这么打$",
        }
        self.guessgame = GuessGame()
    
    def matchPattern(self, msg) -> str:
        '''匹配指令
        
        Args:
            msg: 指令内容
        Returns:
            匹配结果
        '''
        res = None
        for pattern in self.instructions:
            if re.match(self.instructions[pattern], msg):
                res = pattern
        return res

    # 异步初始化
    async def initialize(self):
        pass
        
    @handler(GroupMessageReceived)
    async def msg_received(self, ctx: EventContext):
        msg = str(ctx.event.message_chain).strip()
        pattern = self.matchPattern(msg)
        if not pattern:
            return
        match pattern:
            case "[歌名]是什么歌":
                await querySong(ctx, parseArgs(self.instructions[pattern], msg))
            
            case "chu随机一曲":
                await queryRdnSong(ctx, parseArgs(self.instructions[pattern], msg))
            
            case "添加别名|chuset [歌曲id] [别名1],[别名2],...":
                await queryAddAlias(ctx, parseArgs(self.instructions[pattern], msg))
            
            case "别名[歌曲id|歌曲别名]":
                await queryGetAlias(ctx, parseArgs(self.instructions[pattern], msg))
            
            case "chu lv [难度]":
                await queryLevel(ctx, parseArgs(self.instructions[pattern], msg))
            
            case "chu容错 [歌曲id/别名] [难度]":
                await queryTolerance(ctx, parseArgs(self.instructions[pattern], msg))
            
            case "chuchart [歌曲id/别名] [难度]":
                await queryChart(ctx, parseArgs(self.instructions[pattern], msg))
                
            case "wechart [歌曲id/别名] [难度]":
                await queryChartWE(ctx, parseArgs(self.instructions[pattern], msg))
            
            case "chu曲师 [曲师名]":
                await queryArtist(ctx, parseArgs(self.instructions[pattern], msg))
                
            # case "chu谱师 [谱师名]":
            #     await queryNoteDesigner(ctx, parseArgs(self.instructions[pattern], msg))
            
            case "chu update":
                await queryUpdate(ctx, parseArgs(self.instructions[pattern], msg))
            
            case "chu help":
                await queryHelp(ctx)
            
            case "chu guess [难度]" | "chu guess end" | "guess [歌名]" | "chu hint":
                await queryGuess(ctx, parseArgs(self.instructions[pattern], msg), pattern, self.guessgame)
                
            case "update [分数] [歌名] [难度]":
                await queryUpdScore(ctx, parseArgs(self.instructions[pattern], msg))
            
            case "b30" | "b50":
                await queryQueryBest(ctx, parseArgs(self.instructions[pattern], msg), pattern=pattern)
            
            case "chu copy [服务器]":
                await queryCopy(ctx, parseArgs(self.instructions[pattern], msg))
            
            case "chu bind [服务器] [TOKEN]":
                await queryBind(ctx, parseArgs(self.instructions[pattern], msg))
            # case "[歌名]这里怎么打" | "[歌名]有什么手法" | "[歌名]的[mid]这么打":
            #     await queryMethod(ctx, parseArgs(self.instructions[pattern], msg), pattern, msg)

            case _:
                pass
                        
    # 插件卸载时触发
    def __del__(self):
        pass
