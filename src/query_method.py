import asyncio
import os
import json
import dotenv
import random
import PIL

from pkg.core.entities import LauncherTypes
from pkg.plugin.context import EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import *

from .query_song import searchSong
from .utils.songutil import SongUtil
from .utils.apicaller import MsgPlatform

dotenv.load_dotenv()
SONGS_PATH = os.path.join(os.path.dirname(__file__), "..", os.getenv("SONG_PATH"))
QUESTION_PATH = os.path.join(os.path.dirname(__file__), "..", 'cache', 'methods', 'question')
ANSWER_PATH = os.path.join(os.path.dirname(__file__), "..", 'cache', 'methods', 'answer')

async def download_image(url, filename):
    try:
        msgplatform = MsgPlatform(3000)
        data = await msgplatform.callApi('/download_file', {
            "url": url,
            "name": filename
        })
        return data['data']['file']
    except Exception as e:
        print(f"下载图片时发生错误: {e}") 

async def catchImage(group_id: str, 
                     user_id: str, 
                     command: str,
                     ctx: EventContext,
                     song_index: int,
                     mode: str = "ques",
                     target_id: str = None):
    '''
    下载图片并存储到本地
    
    Args:
        group_id (str): 群号
        user_id (str): 用户号
        command (str): 指令
        ctx (EventContext): 事件上下文
        song_index (int): 歌曲索引
        mode (str, optional): 图片类型. Defaults to "ques".
        target_id (str, optional): 目标id. Defaults to None.
    '''
    payload = {
        "group_id": group_id,
        "count": 3,
        "reverseOrder": True
    }
    msgplatform = MsgPlatform(3000)
    res = await msgplatform.callApi('/get_group_msg_history', payload)
    msgs = res['data']['messages']
    img_info = {
        "id": None,
        "save_path": None,
        "file_name": None,
        "file_type": None,
        "file_size": None,
        "oversize": False,
        "success": False
    }
    img_url = None
    save_path = None
    file_name = None
    print("[SymImage] 搜索指令...")
    if not msgs:
        await ctx.reply(MessageChain([Plain("内部错误")]))
        return img_info
    for msg in msgs:
        if msg['user_id'] == user_id:
            # 消息链长度不为2跳过
            if len(msg['message']) != 2:
                continue
            # 如果第二条text不为指令跳过
            if msg['message'][1]['type'] != "text" or msg['message'][1]['data']['text'] != command:
                continue
            # 第一条为reply，第二条为text
            if msg['message'][0]['type'] == "reply":
                msgplatform = MsgPlatform(3000)
                data = await msgplatform.callApi('/get_msg', {
                    "message_id": msg['message'][0]['data']['id']
                })
                
                # 文件类型/大小
                img_info['file_type'] = data['data']['message'][0]['type']
                img_info['file_size'] = data['data']['message'][0]['data']['file_size']
                
                # 判断是否为图片
                if img_info['file_type']!= "image":
                    await ctx.reply(MessageChain([Plain("请引用图片")]))
                    return img_info
                
                # 判断是否超过10MB
                if int(img_info['file_size']) > 1024 * 1024 * 10:  # 10MB
                    img_info['oversize'] = True
                    return img_info
                
                try:
                    # 下载url
                    img_url = data['data']['message'][0]['data']['url']
                    # 文件名 索引+类型+上传者QQ+随机3位+原文件名
                    id = "".join(random.sample('zyxwvutsrqponmlkjihgfedcba', 3)) if mode == 'ques' else target_id
                    img_info['id'] = id
                    
                    img_info['file_name'] = str(song_index) + "_" + \
                    mode + "_" + id + "_" + str(ctx.event.query.sender_id) + \
                    "_" + data['data']['message'][0]['data']['file']
                    # 获取保存路径
                    save_path = await download_image(img_url, img_info['file_name'])
                    img_info['save_path'] = save_path
                except Exception as e:
                    await ctx.reply(MessageChain([Plain(f"下载图片时发生错误: {e}")]))
                    return img_info
    img_info['success'] = True
    return img_info

async def queryMethod(ctx: EventContext, args: list, pattern: str, msg: str) -> None:
    '''处理猜歌事件
    
    Args:
        ctx (EventContext): 事件上下文
        args (list): 参数列表
    Returns:
        None: 无返回值
    '''
    songs = []
    song_name = args[0]
    matched_songs = searchSong(song_name)
    with open(SONGS_PATH, 'r', encoding='utf-8') as f:
        songs = json.load(f).get("songs")
    if len(matched_songs) == 0:
        await ctx.reply(MessageChain([Plain("没有找到该歌曲，试着输入歌曲全称或其他别名")]))
        return
    elif len(matched_songs) > 1:
        msg_chain = MessageChain([Plain(f"有多个曲目符合条件\n")])
        for songId in matched_songs:
            song_index = songs.index([song for song in songs if song.get('songId') == songId][0])
            msg_chain.append(Plain(f"c{song_index} - {songId}\n"))
        msg_chain.append(Plain(f"\n请使用cid进行精准查询"))
        await ctx.reply(msg_chain)
        return
    songId = matched_songs[0]
    song_index = songs.index([song for song in songs if song.get('songId') == songId][0])
    match pattern:
        case "[歌名]这里怎么打":
            # 存储图片
            img_info = await catchImage(ctx.event.query.launcher_id, ctx.event.query.sender_id, msg, ctx, song_index, "ques")
            if not img_info['success']:
                return
            save_path = img_info['save_path']
            await ctx.reply(MessageChain([Plain(f"手法请求已上传！分配mid为{img_info['id']}\n使用“[歌名]有什么手法”查看已有解析；使用“[歌名]的[mid]这么打”上传手法")]))
            return
        case "[歌名]有什么手法":
            # 查询所有手法
            chunithm_logo_url = "https://chunithm.sega.com/assets/img/common/logo.png"
            chunithm_logo_path = await download_image(chunithm_logo_url, "chunithm_logo.png")
            temp_cache_dir = chunithm_logo_path.replace("chunithm_logo.png", "")
            
            # 筛选temp_cache_dir
            chunithm_ques_methods = []
            chunithm_ans_methods = []
            
            for file in os.listdir(temp_cache_dir):
                # 检查文件名为id+mode+随机3位
                if file.startswith(str(song_index)) and "_ques_" in file:
                    chunithm_ques_methods.append(file)
            if len(chunithm_ques_methods) == 0:
                await ctx.reply(MessageChain([Plain("该曲目暂时没有人发出手法询问，使用“[歌名]这里怎么打”发出询问")]))
                return
            
            # 添加ans
            for file in os.listdir(temp_cache_dir):
                # 检查文件名为id+mode+随机3位
                if file.startswith(str(song_index)) and "_ans_" in file:
                    chunithm_ans_methods.append(file)

            messages = []
            for method in chunithm_ques_methods:
                msg_node = {
                    "type": "node",
                    "data": {
                        "user_id": os.getenv('BOT_QQ'),
                        "nickname": "BOT",
                        "content": [
                            
                        ]
                    }
                }
                # 获取三位字符串
                random_str = method.split("_")[-3].split(".")[0]
                # 获取发送者QQ
                sender_id = method.split("_")[-2]
                # 获取上传者QQ
                msg_node['data']['content'].append({
                    "type": "text",
                    "data": {
                        "text": f"· mid - {random_str}\n上传者： {sender_id}\n"
                    }
                }) 
                img_path = os.path.join(temp_cache_dir, method)
                msg_node['data']['content'].append({
                    "type": "image",
                    "data": {
                        "file": img_path
                    }
                })
                idx = 1
                for ans_method in chunithm_ans_methods:
                    # 匹配id
                    if ans_method.startswith(str(song_index)) and "_ans_" in ans_method:
                        # 匹配随机3位
                        if ans_method.split("_")[-3].split(".")[0] == random_str:
                            img_path = os.path.join(temp_cache_dir, ans_method)
                            # 获取上传者QQ
                            sender_id = ans_method.split("_")[-2]
                            msg_node['data']['content'].append({
                                "type": "text",
                                "data": {
                                    "text": f"· 解法{idx}\n上传者： {sender_id}\n"
                                }
                            })
                            msg_node['data']['content'].append({
                                "type": "image",
                                "data": {
                                    "file": img_path
                                }
                            })
                            idx += 1
                messages.append(msg_node)
                
            message_data = {
                "group_id": str(ctx.event.launcher_id),
                "user_id": "",
                "messages": messages,
                "news": [
                    {"text": f"波师：你总是这个样子"},
                    {"text": f"波师：[图片]"},
                    {"text": f"波师：我们分手吧"}
                ],
                "prompt": "[文件]（秋尼汉化组）业 -善なる神とこの世の悪について-.pdf",
                "summary": "点击浏览",
                "source": f"歌曲: {songId}"
            }
            msgplatform = MsgPlatform(3000)
            await msgplatform.callApi("/send_forward_msg", message_data)
            
        
        case "[歌名]的[mid]这么打":
            # 上传手法
            target_id = args[1]
            img_info = await catchImage(ctx.event.query.launcher_id, ctx.event.query.sender_id, msg, ctx, song_index, "ans", target_id)
            if not img_info['success']:
                return
            save_path = img_info['save_path']
            await ctx.reply(MessageChain([Plain(f"手法已上传！使用“[歌名]有什么手法”查看已有解析")]))
            return