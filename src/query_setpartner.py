import os
import json
import dotenv
import sqlite3

from pkg.plugin.context import EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import *

from .utils.apicaller import MsgPlatform

async def download_image(msgplatform, url, filename):
    try:
        data = await msgplatform.callApi('/download_file', {
            "url": url,
            "name": filename
        })
        print(data)
        return data['data']['file']
    except Exception as e:
        print(f"下载图片时发生错误: {e}")
        local_path = Path(url)
        if os.path.exists(local_path):
            return local_path
        return None

async def catchImage(group_id: str,
                     user_id: str,
                     command: str,
                     reply):
    '''

    return:
        save_path: str, 保存路径
        processed_file_name: str, 处理后的文件名
    '''
    payload = {
        "group_id": group_id,
        "count": 10,
        "reverseOrder": True
    }
    msgplatform = MsgPlatform()
    res = await msgplatform.callApi('/get_group_msg_history', payload)
    msgs = res['data']['messages']
    img_url = None
    save_path = None

    file_name = None
    file_type = None
    file_size = None

    if not msgs:
        print("消息平台错误")
        return None, None

    for msg in msgs:
        if msg['user_id'] == user_id:
            if len(msg['message']) < 2:
                continue
            if msg['message'][0]['type'] == "reply" \
                and msg['message'][1]['type'] == "text" \
                and msg['message'][1]['data']['text'] == command:
                print(f"[CHUNITHMUTILS] {user_id}发出请求：{command}")

                img_info = await msgplatform.callApi('/get_msg', {
                    "message_id": msg['message'][0]['data']['id']
                })
                # 文件类型/大小
                file_type = img_info['data']['message'][0]['type']
                file_size = img_info['data']['message'][0]['data']['file_size']
                if int(file_size) > 1024 * 1024 * 15:  # 15MB
                    print("[CHUNITHMUTILS] 文件过大，请上传小于15MB的文件")
                    return None, {"type": None, "size": None, "oversize": True}
                img_url = img_info['data']['message'][0]['data']['url']
                # xxx.jpg
                file_name = img_info['data']['message'][0]['data']['file']
                save_path = await download_image(msgplatform, img_url, file_name)

    return save_path, {"type": file_type, "size": file_size, "oversize": False}

async def querySetPartner(ctx: EventContext, args: list) -> None:
    _ = args
    save_path, file_info = await catchImage(str(ctx.event.launcher_id), str(ctx.event.user_id), "setpartner", None)
    if save_path is None:
        await ctx.reply(MessageChain([
            Plain("未找到图片，请确保已回复一张图片并发送“setpartner”指令"),
        ]))
        return

    if file_info['oversize']:
        await ctx.reply(MessageChain([
            Plain("图片文件过大，请上传小于15MB的图片"),
        ]))
        return
