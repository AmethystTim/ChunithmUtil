import os
import json
import dotenv

from pkg.plugin.context import EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import *

from .utils.apicaller import *

dotenv.load_dotenv()
SONGS_PATH = os.path.join(os.path.dirname(__file__), "..", os.getenv("SONG_PATH"))

async def queryLevel(ctx: EventContext, args: list) -> None:
    '''查询指定定数的歌曲
    
    Args:
        ctx (EventContext): 事件上下文
        args (list): 参数列表
    Returns:
        None: 无返回值
    '''
    level, = args
    
    songs = []
    matched_songs = []
    
    msgs = "歌曲列表：\n"
    
    with open(SONGS_PATH, "r", encoding="utf-8-sig") as file:
        songs = json.load(file)  
    
    if '+' in level:  # +范围
        target_diff = level.split('+')[0]
        for song in songs:
            for sheet in song.get('sheets'):
                if int(target_diff) + 0.5 <= sheet.get('internalLevelValue') < int(target_diff) + 1:
                    matched_songs.append({
                        "id":songs.index(song),
                        "title":song.get('title'),
                        "internalLevelValue":sheet.get('internalLevelValue')
                    })
    elif '.' in level: # 具体定数
        target_diff = float(level)
        for song in songs:
            for sheet in song.get('sheets'):
                if target_diff == sheet.get('internalLevelValue'):
                    matched_songs.append({
                        "id":songs.index(song),
                        "title":song.get('title'),
                        "internalLevelValue":sheet.get('internalLevelValue')
                    })
    else: # x~x+1定数范围
        target_diff = int(level)
        for song in songs:
            for sheet in song.get('sheets'):
                if int(target_diff) <= sheet.get('internalLevelValue') < int(target_diff) + 1:
                    matched_songs.append({
                        "id":songs.index(song),
                        "title":song.get('title'),
                        "internalLevelValue":sheet.get('internalLevelValue')
                    })
    
    matched_songs.sort(key=lambda x:x.get('internalLevelValue'))
    for matched_song in matched_songs:
        msgs = msgs + f"c{matched_song.get('id')} - {matched_song.get('title')} - {matched_song.get('internalLevelValue')}\n"
    
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
        "source": "定数表"
    }
    msgplatform = MsgPlatform(3000)
    await msgplatform.callApi("/send_forward_msg", message_data)