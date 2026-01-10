import os
import json
import dotenv

from pkg.plugin.context import EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import *

from .utils.apicaller import *

dotenv.load_dotenv()
SONGS_PATH = os.path.join(os.path.dirname(__file__), "..", os.getenv("SONG_PATH"))
VERSION_SONGS_DIR = os.path.join(os.path.dirname(__file__), "..", "cache", "version")

version_alias = {
    "": ["original", "无印", "ori", "初代", "無印"],
    "PLUS": ["无印+", "无印plus", "original+", "original plus", "無印+"],
    "AIR": [],
    "AIR PLUS": ["air+", "air plus"],
    "STAR": [],
    "STAR PLUS": ["star+", "star plus"],
    "AMAZON": [],
    "AMAZON PLUS": ["amazon+", "amazon plus"],
    "CRYSTAL": [],
    "CRYSTAL PLUS": ["crystal+", "crystal plus"],
    "PARADISE": [],
    "PARADISE LOST": ["paradise lost"],
    "NEW": [],
    "NEW PLUS": ["new+", "new plus"],
    "SUN": [],
    "SUN PLUS": ["sun+", "sun plus"],
    "LUMINOUS": ["lmn", "lmns"],
    "LUMINOUS PLUS": ["luminous+", "luminous plus", "lmnp", "lmn+"],
    "VERSE": ["vrs"],
    "X-VERSE": ["x-verse", "xvrs", "xverse"],
    "X-VERSE-X": ["xvx", "xvrsx", "x-versex", "x-verse-x", "sex", "xversex"]
}

def getLatestVersion():
    with open(SONGS_PATH, 'r') as f:
        songs = json.load(f)
        return songs[-1].get('version')

def isHitCache(version: str):
    return os.path.exists(os.path.join(VERSION_SONGS_DIR, version + ".json"))

def convertVersion(version: str):
    '''将用户输入version转化为reina version名'''
    version = version.upper()
    # 检查是否为key
    if version in version_alias.keys():
        return version
    # 检查是否在别名列表
    version = version.lower()
    for key in version_alias.keys():
        if version in version_alias[key]:
            return key
    # 读取songs.json，倒序检查有无匹配version
    version = version.upper()
    with open(SONGS_PATH, 'r') as f:
        songs = json.load(f)
        songs.reverse()
    for song in songs:
        # 寻找到最近一次有别名的版本为止
        if song.get('version') in version_alias.keys():
            return None
        if song.get('version') == version:
            return song.get('version')
    return None

async def queryVersion(ctx: EventContext, args: list) -> None:
    '''查询指定版本的歌曲
    
    Args:
        ctx (EventContext): 事件上下文
        args (list): 参数列表
    Returns:
        None: 无返回值
    '''
    version, = args
    version_ = convertVersion(version)
    if version_ == None:
        await ctx.reply(f"未知版本：{version}，请尝试其他版本别名")
        return
    
    songs = []
    matched_songs = []
    
    msgs = f"{version_}歌曲列表：\n"
    
    if isHitCache(version_) and version_ != getLatestVersion():
        with open(os.path.join(VERSION_SONGS_DIR, version_ + ".json")) as file:
            matched_songs = json.load(file)
    else:
        with open(SONGS_PATH, "r", encoding="utf-8-sig") as file:
            songs = json.load(file)  
            songs.reverse()
            for song in songs:
                if len(matched_songs) >= 1 and song.get('title') == matched_songs[-1].get('title'):
                    continue
                if song.get('version') == version_:
                    matched_songs.append(song)
            matched_songs.reverse()
            with open(os.path.join(VERSION_SONGS_DIR, version_ + ".json"), "w") as cahce_f:
                json.dump(matched_songs, cahce_f, ensure_ascii=False, indent=4)
                print(f"缓存版本{version_}")
    
    for matched_song in matched_songs:
        msgs = msgs + f"c{matched_song.get('idx')} - {matched_song.get('title')} - {matched_song.get('const')}\n"
    
    message_data = {
        "group_id": str(ctx.event.launcher_id),
        "user_id": "",
        "messages": [
            {
                "type": "node",
                "data": {
                    "user_id": "114514",
                    "nickname": "BOT",
                    "content": [
                        {
                            "type": "text",
                            "data": {
                                "text": f"{msgs}"
                            }
                        }
                    ]
                }
            }
        ],
        "news": [
            {"text": f"波师：国服追上日服进度了"},
            {"text": f"波师：[图片]"},
            {"text": f"波师：居然还换了120hz框"}
        ],
        "prompt": "[文件]年度学习资料.zip",
        "summary": "点击浏览",
        "source": f"{version_}版本歌曲列表"
    }
    msgplatform = MsgPlatform(3000)
    await msgplatform.callApi("/send_forward_msg", message_data)