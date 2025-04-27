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
from .src.query_notedesigner import *
from .src.query_level import *

from .src.utils.argsparser import *

dotenv.load_dotenv()
utils_dir = os.path.join(os.path.dirname(__file__), 'src', 'utils')

# 注册插件
@register(name="ChunithmUtil", description="集成多项Chunithm实用功能的LangBot插件🧩", version="1.1", author="Amethyst")
class ChunithmUtilPlugin(BasePlugin):
    # 插件加载时触发
    def __init__(self, host: APIHost):
        # subprocess.run(["python", os.path.join(utils_dir, "songmeta.py")], capture_output=True, text=True)
        # subprocess.run(["python", os.path.join(utils_dir, "mapping.py")], capture_output=True, text=True)
        
        self.instructions = {
            "chu help": 
                r"^chu help$",
            "[歌名]是什么歌": 
                r"^(.+)是什么歌$",
            "chu随机一曲": 
                r"^chu随机[一曲]*$",
            "添加别名|alias [歌曲id] [别名1],[别名2],...": 
                r"(?:^添加别名|alias) (c\d+)\s+((?:[^,，]+[,，]?)+)$",
            "别名[歌曲id|歌曲别名]": 
                r"^别名\s*(.+)$",
            "chu lv [难度]": 
                r"^chu lv (\S+)$",
            "chu容错 [歌曲id/别名] [难度]": 
                r"^chu容错 (c\d+|.+?)(?: (exp|mas|ult))?$",
            "chuchart [歌曲id/别名] [难度]": 
                r"^chuchart (c\d+|.+?)(?: (exp|mas|ult))?$",
            "chu曲师 [曲师名]" : 
                r"^chu(?:^曲师| qs) (.+)$",
            "chu谱师 [谱师名]": 
                r"^chu(?:^谱师| ps) (.+)$",
        }
    
    def matchPattern(self, msg):
        '''匹配指令
        
        Args:
            msg: 指令内容
        Returns:
            匹配结果
        '''
        for pattern in self.instructions:
            if re.match(self.instructions[pattern], msg):
                self.ap.logger.info(f"指令匹配：{pattern}")
                return pattern
        return None

    # 异步初始化
    async def initialize(self):
        pass
        
    @handler(GroupMessageReceived)
    @handler(PersonMessageReceived)
    async def msg_received(self, ctx: EventContext):
        msg = str(ctx.event.message_chain).strip()
        instruction = self.matchPattern(msg)
        if not instruction:
            return
        match instruction:
            case "[歌名]是什么歌":
                await querySong(ctx, parseArgs(self.instructions[instruction], msg))
            
            case "chu随机一曲":
                await queryRdnSong(ctx, parseArgs(self.instructions[instruction], msg))
            
            case "添加别名|alias [歌曲id] [别名1],[别名2],...":
                await queryAddAlias(ctx, parseArgs(self.instructions[instruction], msg))
            
            case "别名[歌曲id|歌曲别名]":
                await queryGetAlias(ctx, parseArgs(self.instructions[instruction], msg))
            
            case "chu lv [难度]":
                await queryLevel(ctx, parseArgs(self.instructions[instruction], msg))
            
            case "chu容错 [歌曲id/别名] [难度]":
                await queryTolerance(ctx, parseArgs(self.instructions[instruction], msg))
            
            case "chuchart [歌曲id/别名] [难度]":
                await queryChart(ctx, parseArgs(self.instructions[instruction], msg))
            
            case "chu曲师 [曲师名]":
                await queryArtist(ctx, parseArgs(self.instructions[instruction], msg))
                
            case "chu谱师 [谱师名]":
                await queryNoteDesigner(ctx, parseArgs(self.instructions[instruction], msg))
            
            case "chu help":
                await queryHelp(ctx)
            
            case _:
                pass
                        
    # 插件卸载时触发
    def __del__(self):
        pass
