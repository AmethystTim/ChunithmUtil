import os
import os.path as osp
import json
import dotenv
import sqlite3
import numpy as np

from pkg.plugin.context import EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import *

from .query_song import searchSong
from .utils.songutil import *
from .utils.apicaller import *

dotenv.load_dotenv()
SONGS_PATH = os.path.join(os.path.dirname(__file__), "..", os.getenv("SONG_PATH"))
DB_PATH = os.path.join(os.path.dirname(__file__), "..", 'data', 'data.db')

def getRank(score: int) -> str:
    if score >= 1009000:
        return "SSS+"
    elif score >= 1007500:
        return "SSS"
    elif score >= 1005000:
        return "SS+"
    elif score >= 1000000:
        return "SS"
    elif score >= 990000:
        return "S+"
    elif score >= 975000:
        return "S"
    return "S-"

def convertRank(rank: str):
    match rank:
        case "sssp":
            return "SSS+"
        case "sss":
            return "SSS"
        case "ssp":
            return "SS+"
        case "ss":
            return "SS"
        case "sp":
            return "S+"
        case "s":
            return "S"
        case _:
            return "S-"

def getSongInfo(cids: np.ndarray, difficulty: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    '''获取歌曲信息
    
    Returns:
        const, name: 歌曲定数，歌曲名
    '''
    const = []
    name = []
    deleted = []
    cids = np.asarray(cids).ravel()
    difficulty = np.asarray(difficulty).ravel()
    with open(SONGS_PATH, 'r', encoding='utf-8-sig') as f:
        songs = json.load(f)
        for cid, diff in zip(cids, difficulty):
            targets = []
            name_to_append = None
            print(f"cid: {cid}, diff: {diff}")
            for song in songs:
                if song.get('idx') == str(cid):
                    targets.append(song.get('const'))
                    name_to_append = song.get('title')
            if not targets == []:
                const.append(targets[diff])
                name.append(name_to_append)
            else:
                const.append(0.0)
                name.append(None)
                deleted.append(cid)
    const = np.array(const).astype(float)
    name = np.array(name)
    return const, name, deleted

def calcRating(const: np.ndarray, score: np.ndarray) -> np.ndarray:
    '''计算歌曲Rating值
    
    Args:
        const (np.ndarray): 歌曲定数
        score (np.ndarray): 分数
    Returns:
        rating (np.ndarray): rating值
    '''
    def getBias(score: np.ndarray) -> np.ndarray:
        """计算偏移值"""
        score = np.asarray(score, dtype=float)
        bias = np.zeros_like(score)

        # < 500000
        mask = score < 500000
        bias[mask] = 0

        # 500000 - 799999: 0 → -2.5
        mask = (score >= 500000) & (score < 800000)
        progress = (score[mask] - 500000) / 300000
        bias[mask] = progress * (-2.5)

        # 800000 - 899999: -2.5 → -5.0
        mask = (score >= 800000) & (score < 900000)
        base = -2.5
        target = -5.0
        progress = (score[mask] - 800000) / 100000
        bias[mask] = base + (target - base) * progress

        # 900000 - 924999: -5.0 → -3.0
        mask = (score >= 900000) & (score < 925000)
        base = -5.0
        target = -3.0
        progress = (score[mask] - 900000) / 25000
        bias[mask] = base + (target - base) * progress

        # 925000 - 974999: -3.0 → 0
        mask = (score >= 925000) & (score < 975000)
        base = -3.0
        target = 0.0
        progress = (score[mask] - 925000) / 50000
        bias[mask] = base + (target - base) * progress

        # 975000 - 999999: 0 → 1.0
        mask = (score >= 975000) & (score < 1000000)
        progress = (score[mask] - 975000) / 25000
        bias[mask] = 0 + (1.0 - 0) * progress

        # 1000000 - 1004999: 1.0 → 1.5
        mask = (score >= 1000000) & (score < 1005000)
        base = 1.0
        target = 1.5
        progress = (score[mask] - 1000000) / 5000
        bias[mask] = base + (target - base) * progress

        # 1005000 - 1007499: 1.5 → 2.0
        mask = (score >= 1005000) & (score < 1007500)
        base = 1.5
        target = 2.0
        progress = (score[mask] - 1005000) / 2500
        bias[mask] = base + (target - base) * progress

        # 1007500 - 1008999: 2.0 → 2.15
        mask = (score >= 1007500) & (score < 1009000)
        base = 2.0
        target = 2.15
        progress = (score[mask] - 1007500) / 1500
        bias[mask] = base + (target - base) * progress

        # >= 1009000: = 2.15
        mask = score >= 1009000
        bias[mask] = 2.15

        return bias

    bias = getBias(score)
    rating = (const + bias).astype(float).round(2)
    return rating

async def queryBest30(ctx: EventContext, user_id: str, use_simple=False):
    '''查询b30'''
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(f"SELECT * FROM record WHERE user_id='{user_id}'")
        records = c.fetchall()
        if len(records) == 0:
            await ctx.reply(MessageChain([Plain(f"你还没有记录哦")]))
        records = np.array([list(record) for record in records])
        cids = np.copy(records[:, 1])
        difficulty = np.copy(records[:, 3]).astype(int)
        const, name, _ = getSongInfo(cids, difficulty)
        score = np.copy(records[:, 2])
        rating = calcRating(const, score)
        # 增加name列
        concatenated = np.concatenate((records, name.reshape(-1, 1)), axis=1)
        # 增加const列
        concatenated = np.concatenate((concatenated, const.reshape(-1, 1)), axis=1)
        # 按照rating降序排列
        rating = np.array(rating, dtype=float)
        idx_desc = np.argsort(rating)[::-1]
        rating = rating[idx_desc]
        concatenated = concatenated[idx_desc]
        # 增加rating列
        concatenated = np.concatenate((concatenated, rating.reshape(-1, 1)), axis=1)
        # 去除user_id列
        sorted_records = concatenated[:30, 1:]
        # 处理cid列
        sorted_records[:, 0] = ["c" + str(x) for x in sorted_records[:, 0]]
        # 处理difficulty列
        songutil = SongUtil()
        sorted_records[:, 2] = [songutil.getIndex2Diff(int(x)) for x in sorted_records[:, 2]]
        try:
            average_rating = np.sum(sorted_records[:, -1].astype(float)) / 30.0
        except Exception as e:
            average_rating = 0.0
            await ctx.reply(MessageChain([Plain(f"计算错误，{e}")]))
        # 仅返回文本
        if use_simple:
            # [cid, score, difficulty, name, const, rating] -> [cid, name, difficulty, score, rating]
            cols = [0, 3, 2, 1, 5]  # cid, name, difficulty, score, rating
            result = sorted_records[:, cols]
            msgs = []
            for i, record in enumerate(result):
                unit = {
                    "type": "node",
                    "data": {
                        "user_id": "114514",
                        "nickname": f"B{i+1}",
                        "content": [
                            {
                                "type": "text",
                                "data": {
                                    "text": f"{record[0]} - {record[1]}\n{record[2]}\n{record[3]} - {record[4]}"
                                }
                            }
                        ]
                    }
                }
                msgs.append(unit)
            message_data = {
                "group_id": str(ctx.event.launcher_id),
                "user_id": "",
                "messages": msgs,
                "news": [
                    {"text": f"你的B30均值为{average_rating:.3f}"},
                ],
                "prompt": "[文件]年度学习资料.zip",
                "summary": "点击浏览",
                "source": "CHUNITHM Best30"
            }
            msgplatform = MsgPlatform(3000)
            await msgplatform.callApi("/send_forward_msg", message_data)
        # 返回完整分表图片
        else:
            pass
    except sqlite3.Error as e:
        print(e)
        return -1, f"查询失败，{e}"

async def queryQueryBest(ctx: EventContext, args: list, **kwargs) -> None:
    '''查询最佳
    
    Args:
        ctx (EventContext): 事件上下文
        args (list): 参数列表
    Returns:
        None: 无返回值
    '''
    use_simple, = args
    use_simple = True if use_simple else False
    user_id = str(ctx.event.sender_id)
    pattern = kwargs .get('pattern', None)
    match pattern:
        case 'b30':
            await ctx.reply(MessageChain([Plain(f"正在查询Best30...")]))
            await queryBest30(ctx, user_id, use_simple=use_simple)
        case 'b50':
            await ctx.reply(MessageChain([Plain(f"前面的区域以后再探索吧！")]))
        case _:
            await ctx.reply(MessageChain([Plain(f"未知指令：{pattern}")]))
    
    
    
    