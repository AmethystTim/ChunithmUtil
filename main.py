import PIL.Image
from pkg.plugin.context import register, handler, BasePlugin, APIHost, EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import *
import random
import re
import os
import json
import dotenv
import difflib
import PIL
from io import BytesIO
from plugins.ChunithmUtil.forward import forward_message
from plugins.ChunithmUtil.utils.cover_cache import *
from pkg.platform.types.message import Image as image_langbot

# 读取.env 文件中的环境变量
dotenv.load_dotenv()
cover_cache_dir = os.path.join(os.path.dirname(__file__), './cache/covers')
chart_cache_dir = os.path.join(os.path.dirname(__file__), './cache/charts')

# 注册插件
@register(name="ChunithmUtil", description="学习下正则查歌", version="1.0", author="Amethyst")
class ChunithmUtilPlugin(BasePlugin):
    # 插件加载时触发
    def __init__(self, host: APIHost):
        self.forward_message = forward_message(host="127.0.0.1", port=3000)
        self.diff2index = {
            "adv": 1,
            "exp": 2,
            "mas": 3,
            "ult": 4,
        }
        self.instructions = {
            "chu查歌[歌名]": r"^chu查歌\s*(.+)$",
            "chu随机一曲": r"^chu随机[一曲]*$",
            "添加别名|alias [歌曲id] [别名1],[别名2],...": r"(^添加别名|alias) (c\d+)\s+((?:[^,，]+[,，]?)+)$",
            "[歌名]是什么歌": r"^(.+)是什么歌$",
            "别名[歌曲id|歌曲别名]": r"^别名\s*(.+)$",
            "chu lv [难度]": r"^chu lv (\S+)$",
            "chu容错 [歌曲id/别名] [难度]": r"^chu容错 (c\d+|.+?)(?: (exp|mas|ult))?$",
            "chuchart [歌曲id/别名] [难度]": r"^chuchart (c\d+|.+?)(?: (exp|mas|ult))?$",
        }
    
    def matchPattern(self, msg):
        '''
        匹配指令
        
        args:
            msg: 指令内容
        return:
            匹配结果
        '''
        for pattern in self.instructions:
            if re.match(self.instructions[pattern], msg):
                self.ap.logger.info(f"指令匹配：{pattern}")
                return pattern
        return None
    
    def fuzzySearch(self, query: str, songs: list):
        '''
        模糊搜索
        
        args:
            query: 查询字符串
            songs: 选项列表
        return:
            匹配结果
        '''
        query = query.lower()
        choices_case_nonsensitive = [song.get('songId').lower() for song in songs]
        # 模糊搜索
        results = difflib.get_close_matches(query, choices_case_nonsensitive, n=15, cutoff=0.8)
        results = [songs[choices_case_nonsensitive.index(result)] for result in results]
        results = [{"id": songs.index(result), "songId": result.get('songId')} for result in results]
        # 子串匹配
        for song in songs:
            if query in song.get('songId').lower():
                results.append({"id": songs.index(song), "songId": song.get('songId')})
        return results
    
    def getChartID(self, song):
        with open(os.path.join(os.path.dirname(__file__), os.getenv("ID2NAME_PATH")), "r", encoding="utf-8") as f:
            f = json.load(f)
            res = difflib.get_close_matches(song['songId'], f.values(), n=15, cutoff=0.9)
            if len(res) > 0:
                id = list(f.keys())[list(f.values()).index(res[0])]
                return id
        return None
    
    def getChartGen(self, chartID):
        with open(os.path.join(os.path.dirname(__file__), os.getenv("ID2GEN_PATH")), "r", encoding="utf-8") as f:
            f = json.load(f)
            return f.get(chartID)
    
    def concatChartUrl(self, chartID, gen, diff = "mas"):
        charturl = os.getenv("CHART_URL")
        bgurl = os.getenv("CHART_BG_URL")
        barurl = os.getenv("CHART_BAR_URL")
        charturl = charturl.replace("<chartid>", chartID)
        bgurl = bgurl.replace("<chartid>", chartID)
        barurl = barurl.replace("<chartid>", chartID)
        if diff == 'ult':
            charturl = charturl.replace("mst.png", f"{diff}.png").replace("<gen>", diff)
            bgurl = bgurl.replace("<gen>", diff)
            barurl = barurl.replace("<gen>", diff)
        else:
            charturl = charturl.replace("<gen>", gen)
            bgurl = bgurl.replace("<gen>", gen)
            barurl = barurl.replace("<gen>", gen)
        if diff != "mas":
            charturl = charturl.replace("mst.png", f"{diff}.png")
        return charturl, bgurl, barurl
    
    def checkChartCache(self, chartid, difficulty):
        return os.path.exists(os.path.join(chart_cache_dir, f"{chartid}_{"" if difficulty == "mas" else difficulty}.png"))
    
    async def searchSong(self, ctx: EventContext, song_name: str):
        songs = []  # 歌曲列表
        song = None # 歌曲字典
        matched_songs = []  # 匹配歌曲ID列表
        if song_name.startswith('c') and all(char.isdigit() for char in song_name[1:]):   # 查歌曲索引
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.getenv("SONG_PATH")), "r", encoding="utf-8") as file:
                songs = json.load(file).get("songs")
                song_index = int(song_name[1:])
                song = songs[song_index]
        else:  # 别名/模糊查歌
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.getenv("SONG_PATH")), "r", encoding="utf-8") as file:
                songs = json.load(file).get("songs")
                # 在alias.json中查找别名
                with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.getenv("ALIAS_PATH")), "r", encoding="utf-8") as file:
                    songs_alias = json.load(file).get("songs")  # alias.json歌曲列表
                    for song_alias in songs_alias:  # 歌曲
                        for alias in song_alias.get('aliases'): # 遍历歌曲所有别名
                            if alias == song_name:  # 别名采用精准匹配
                                tmp_list = [s.get('songId') for s in songs] # 为获取索引临时构造songId列表
                                matched_songs.append({"id":tmp_list.index(song_alias.get('songId')),"songId":song_alias.get('songId')})
                    self.ap.logger.info(f"别名匹配结果：{matched_songs}")
                    # 在data.json中模糊搜索
                    matched_songs.extend(self.fuzzySearch(song_name, songs))
                    self.ap.logger.info(f"模糊匹配+别名匹配结果：{matched_songs}")
                matched_songs = {json.dumps(d, sort_keys=True): d for d in matched_songs}   # 去重
                matched_songs = list(matched_songs.values())
                return matched_songs
    
    def calcTolerance(self, noteCounts: dict) -> dict:
        '''
        计算100小/50小情况下的鸟/鸟加容错
        '''
        total_score = 10_10000  # 理论值分数
        total_notes = noteCounts.get("total")
        justice_loss = 0.01 * (total_score / total_notes)    # 小J损失分数
        attack_loss = (50/101) * (total_score / total_notes)    # attack损失分数
        # 鸟容错计算
        _7500_loss = 2500 
        # 100小
        _7500_justice_loss_100 = 100*justice_loss
        _7500_max_attack_num_100 = (_7500_loss - _7500_justice_loss_100)//attack_loss
        # 50小
        _7500_justice_loss_50 = 50*justice_loss
        _7500_max_attack_num_50 = (_7500_loss - _7500_justice_loss_50)//attack_loss
        # 鸟加容错
        _9000_loss = 1000
        # 100小
        _9000_justice_loss_100 = 100*justice_loss
        _9000_max_attack_num_100 = (_9000_loss - _9000_justice_loss_100)//attack_loss
        # 50小
        _9000_justice_loss_50 = 50*justice_loss
        _9000_max_attack_num_50 = (_9000_loss - _9000_justice_loss_50)//attack_loss
        return dict({
            "1007500": {
                "100j": int(_7500_max_attack_num_100),
                "50j": int(_7500_max_attack_num_50),
            },
            "1009000": {
                "100j": int(_9000_max_attack_num_100),
                "50j": int(_9000_max_attack_num_50),
            }
        })    
    
    # 异步初始化
    async def initialize(self):
        pass

    # 当收到群消息时触发
    @handler(GroupMessageReceived)
    async def group_message_received(self, ctx: EventContext):
        msg = str(ctx.event.message_chain)
        sender_id = ctx.event.query.message_event.sender.id # 获取发送消息的用户 ID
        sender_name = ctx.event.query.message_event.sender.get_name() # 获取发送消息的用户名称
        instruction = self.matchPattern(msg)
        if instruction:
            match instruction:
                case "[歌名]是什么歌":
                    matched_songs = []  # 匹配歌曲ID列表
                    song_name = re.search(r"^(.+)是什么歌$", msg).group(1)
                    self.ap.logger.info(f"查歌：{song_name}")
                    songs = []  # 歌曲列表
                    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.getenv("SONG_PATH")), "r", encoding="utf-8") as file:
                        songs = json.load(file).get("songs")
                        # 在alias.json中查找别名
                        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.getenv("ALIAS_PATH")), "r", encoding="utf-8") as file:
                            songs_alias = json.load(file).get("songs")  # alias.json歌曲列表
                            for song_alias in songs_alias:  # 歌曲
                                for alias in song_alias.get('aliases'): # 遍历歌曲所有别名
                                    if alias == song_name:  # 别名采用精准匹配
                                        tmp_list = [s.get('songId') for s in songs] # 为获取索引临时构造songId列表
                                        matched_songs.append({"id":tmp_list.index(song_alias.get('songId')),"songId":song_alias.get('songId')})
                            self.ap.logger.info(f"别名匹配结果：{matched_songs}")
                            # 在data.json中模糊搜索
                            matched_songs.extend(self.fuzzySearch(song_name, songs))
                            self.ap.logger.info(f"模糊匹配结果：{matched_songs}")

                    matched_songs = {json.dumps(d, sort_keys=True): d for d in matched_songs}   # 去重
                    matched_songs = list(matched_songs.values())
                    if matched_songs and len(matched_songs) == 1:   # 只有一个符合直接返回
                        song_index = int(matched_songs[0].get('id'))
                        if 0 <= song_index < len(songs):
                            song = songs[song_index]
                            checkIsHit(os.getenv('COVER_URL'), song.get('imageName'))
                            img_conponent = await Image.from_local(os.path.join(cover_cache_dir, song.get('imageName')))
                            msg_chain = MessageChain([Plain(f"c{song_index} - {song.get('title')}\nby {song.get('artist')}")])
                            for sheet in song.get('sheets'):
                                msg_chain.append(Plain(f"\n{str(sheet.get('difficulty')).capitalize()} {sheet.get('internalLevelValue')}"))
                            msg_chain.append(img_conponent)
                            await ctx.reply(msg_chain)
                            return
                    elif matched_songs and len(matched_songs) > 1:  # 多个符合使用精准匹配查歌
                        msg_chain = MessageChain([Plain(f"有多个曲目符合条件\n")])
                        for song in matched_songs:
                            msg_chain.append(Plain(f"c{song.get('id')} - {song.get('songId')}\n"))
                        msg_chain.append(Plain(f"\n请使用“chu查歌 [歌曲ID]”进行精准查询"))
                        await ctx.reply(msg_chain)
                    else:
                        await ctx.reply(MessageChain([Plain("没有找到该歌曲，试着输入歌曲全称")]))
                        return
                case "chu随机一曲":
                    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.getenv("SONG_PATH")), "r", encoding="utf-8") as file:
                        songs = json.load(file).get("songs")
                        song = random.choice(songs)
                        checkIsHit(os.getenv('COVER_URL'), song.get('imageName'))
                        img_conponent = await Image.from_local(os.path.join(cover_cache_dir, song.get('imageName')))
                        msg_chain = MessageChain([Plain(f"{song.get('title')}\nby {song.get('artist')}")])
                        for sheet in song.get('sheets'):
                            msg_chain.append(Plain(f"\n{str(sheet.get('difficulty')).capitalize()} {sheet.get('internalLevelValue')}"))
                        msg_chain.append(img_conponent)
                        await ctx.reply(msg_chain)
                case "chu查歌[歌名]":
                    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.getenv("SONG_PATH")), "r", encoding="utf-8") as file:
                        songs = json.load(file).get("songs")
                        song_name = re.search(r"^chu查歌\s*(.+)$", msg).group(1)
                        for song in songs:  # 查songId
                            if song.get('songId') == song_name:
                                checkIsHit(os.getenv('COVER_URL'), song.get('imageName'))
                                img_conponent = await Image.from_local(os.path.join(cover_cache_dir, song.get('imageName')))
                                msg_chain = MessageChain([Plain(f"c{songs.index(song)} - {song.get('title')}\nby {song.get('artist')}")])
                                for sheet in song.get('sheets'):
                                    msg_chain.append(Plain(f"\n{str(sheet.get('difficulty')).capitalize()} {sheet.get('internalLevelValue')}"))
                                msg_chain.append(img_conponent)
                                await ctx.reply(msg_chain)
                                return
                        if song_name.startswith('c'):   # 查歌曲索引
                            song_index = int(song_name[1:])
                            if 0 <= song_index < len(songs):
                                song = songs[song_index]
                                checkIsHit(os.getenv('COVER_URL'), song.get('imageName'))
                                img_conponent = await Image.from_local(os.path.join(cover_cache_dir, song.get('imageName')))
                                msg_chain = MessageChain([Plain(f"{song_name} - {song.get('title')}\nby {song.get('artist')}")])
                                for sheet in song.get('sheets'):
                                    msg_chain.append(Plain(f"\n{str(sheet.get('difficulty')).capitalize()} {sheet.get('internalLevelValue')}"))
                                msg_chain.append(img_conponent)
                                await ctx.reply(msg_chain)
                                return
                            
                        await ctx.reply(MessageChain([Plain(f"没有找到{song_name}，试着输入歌曲全称或使用模糊搜索")]))
                case "添加别名|alias [歌曲id] [别名1],[别名2],...":
                    songs = []  # 歌曲列表
                    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.getenv("SONG_PATH")), "r", encoding="utf-8") as file:
                        songs = json.load(file).get("songs")
                    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.getenv("ALIAS_PATH")), "r", encoding="utf-8") as file:
                        songs_aliases = json.load(file).get("songs")  # alias.json歌曲列表
                        re_match = re.search(r"(^添加别名|alias) (c\d+)\s+((?:[^,，]+[,，]?)+)$", msg)
                        id = re_match.group(2)
                        aliases = re.split(r"[，,]",re_match.group(3))
                        if not aliases:
                            await ctx.reply(MessageChain([Plain(f"别名不能为空")]))
                            return
                        self.ap.logger.info(f"歌曲ID：{id}")
                        self.ap.logger.info(f"待添加别名：{aliases}")
                        if id.startswith('c'):   # 查歌曲索引
                            song_index = int(id[1:])    # 歌曲索引
                            if 0 <= song_index < len(songs):
                                song = songs[song_index]    # 获取歌曲信息
                                song_id = song.get('songId')    # 获取songId
                                for song_aliases in songs_aliases:  # 在alias.json匹配歌曲
                                    if song_aliases.get('songId') == song_id:  # 歌曲ID匹配
                                        available_aliases = []  # 别名添加成功列表
                                        unavailable_aliases = []  # 别名添加失败列表
                                        for alias in aliases:   # 逐个添加别名
                                            if not alias in song_aliases.get('aliases'):  # 别名不存在
                                                song_aliases.get('aliases').append(alias)  # 别名添加到歌曲别名列表
                                                available_aliases.append(alias) # 别名添加成功列表
                                            else:
                                                unavailable_aliases.append(alias) # 别名添加失败列表
                                        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.getenv("ALIAS_PATH")), "w", encoding="utf-8") as file:
                                            json.dump({"songs":songs_aliases}, file, indent=4, ensure_ascii=False)
                                        msg_chain = MessageChain([])
                                        if len(available_aliases) > 0:
                                            msg_chain.append(Plain(f"歌曲{song_id}的别名{'，'.join(available_aliases)}添加成功\n"))
                                        if len(unavailable_aliases) > 0:
                                            msg_chain.append(Plain(f"歌曲{song_id}的别名{'，'.join(unavailable_aliases)}添加失败"))
                                        await ctx.reply(msg_chain)
                                        return
                                song_aliases = {"songId":song_id, "aliases":[]} # 创建新歌曲别名列表
                                available_aliases = []  # 别名添加成功列表
                                unavailable_aliases = []  # 别名添加失败列表
                                for alias in aliases:   # 逐个添加别名
                                    if not alias in song_aliases.get('aliases'):  # 别名不存在
                                        song_aliases.get('aliases').append(alias)  # 别名添加到歌曲别名列表
                                        available_aliases.append(alias) # 别名添加成功列表
                                    else:
                                        unavailable_aliases.append(alias) # 别名添加失败列表
                                songs_aliases.append(song_aliases) # 别名添加到alias.json
                                with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.getenv("ALIAS_PATH")), "w", encoding="utf-8") as file:
                                    json.dump({"songs":songs_aliases}, file, indent=4, ensure_ascii=False)
                                msg_chain = MessageChain([])
                                if len(available_aliases) > 0:
                                    msg_chain.append(Plain(f"歌曲{song_id}的别名{'，'.join(available_aliases)}添加成功\n"))
                                if len(unavailable_aliases) > 0:
                                    msg_chain.append(Plain(f"歌曲{song_id}的别名{'，'.join(unavailable_aliases)}添加失败"))
                                await ctx.reply(msg_chain)
                                return
                case "别名[歌曲id|歌曲别名]":
                    songs = []  # 歌曲列表
                    id = re.search(r"^别名\s*(.+)$", msg).group(1)
                    # 获取songId
                    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.getenv("SONG_PATH")), "r", encoding="utf-8") as file:
                        songs = json.load(file).get("songs")
                    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.getenv("ALIAS_PATH")), "r", encoding="utf-8") as file:
                        songs_aliases = json.load(file).get("songs")  # alias.json歌曲列表
                    if id.startswith('c'):   # 查歌曲索引
                        song_index = int(id[1:])    # 歌曲索引
                        if 0 <= song_index < len(songs):
                            song = songs[song_index]    # 获取歌曲信息
                            song_id = song.get('songId')    # 获取songId
                        for song_alias in songs_aliases:  # 在alias.json匹配歌曲
                            if song_alias.get('songId') == song_id:  # 歌曲ID匹配
                                aliases = song_alias.get('aliases')
                                if aliases:  # 歌曲有别名
                                    msg_chain = MessageChain([Plain(f"歌曲{song_id}的别名：")])
                                    for alias in aliases:
                                        msg_chain.append(Plain(f"\n· {alias}"))
                                    await ctx.reply(msg_chain)
                                    return
                                else:  # 歌曲无别名
                                    await ctx.reply(MessageChain([Plain(f"歌曲{song_id}暂无别名")]))
                                    return
                        # 歌曲ID未匹配
                        await ctx.reply(MessageChain([Plain(f"歌曲{song_id}不存在或暂无别名")]))
                        return
                    else:   # 使用歌曲别名
                        matched_songs = []  # 匹配歌曲ID列表
                        for song_alias in songs_aliases:  # 歌曲
                            for alias in song_alias.get('aliases'): # 遍历歌曲所有别名
                                if alias == id:  # 别名采用精准匹配
                                    tmp_list = [s.get('songId') for s in songs] # 为获取索引临时构造songId列表
                                    matched_songs.append({"id":tmp_list.index(song_alias.get('songId')),"songId":song_alias.get('songId')})
                        if matched_songs and len(matched_songs) == 1:   # 只有一个符合直接返回
                            song_index = int(matched_songs[0].get('id'))
                            songId = matched_songs[0].get('songId')
                            # 在alias.json中查找别名
                            for song_alias in songs_aliases:
                                if song_alias.get('songId') == songId:  # 歌曲ID匹配
                                    aliases = song_alias.get('aliases')
                                    if aliases:  # 歌曲有别名
                                        msg_chain = MessageChain([Plain(f"歌曲{songId}的别名：")])
                                        for alias in aliases:
                                            msg_chain.append(Plain(f"\n· {alias}"))
                                        await ctx.reply(msg_chain)
                                        return
                                    else:  # 歌曲无别名
                                        await ctx.reply(MessageChain([Plain(f"歌曲{songId}暂无别名")]))
                                        return
                        elif matched_songs and len(matched_songs) > 1:  # 多个符合使用精准匹配查歌
                            msg_chain = MessageChain([Plain(f"有多个曲目符合条件\n")])
                            for song in matched_songs:
                                msg_chain.append(Plain(f"c{song.get('id')} - {song.get('songId')}\n"))
                            msg_chain.append(Plain(f"\n请使用“别名 [歌曲ID]”进行精准查询"))
                            await ctx.reply(msg_chain)
                        else:
                            await ctx.reply(MessageChain([Plain(f"没有找到{id}")]))
                case "chu lv [难度]":
                    songs = []  # 歌曲列表
                    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.getenv("SONG_PATH")), "r", encoding="utf-8") as file:
                        songs = json.load(file).get("songs")
                    difficulty = re.search(r"^chu lv (\S+)$", msg).group(1)
                    matched_songs = []  # 匹配歌曲ID列表
                    msgs = "歌曲列表：\n"
                    if '+' in difficulty:  # +范围
                        target_diff = difficulty.split('+')[0]
                        for song in songs:
                            for sheet in song.get('sheets'):
                                if int(target_diff) + 0.5 <= sheet.get('internalLevelValue') < int(target_diff) + 1:
                                    matched_songs.append({
                                        "id":songs.index(song),
                                        "title":song.get('title'),
                                        "internalLevelValue":sheet.get('internalLevelValue')
                                    })
                    elif '.' in difficulty: # 具体定数
                        target_diff = float(difficulty)
                        for song in songs:
                            for sheet in song.get('sheets'):
                                if target_diff == sheet.get('internalLevelValue'):
                                    matched_songs.append({
                                        "id":songs.index(song),
                                        "title":song.get('title'),
                                        "internalLevelValue":sheet.get('internalLevelValue')
                                    })
                    else: # x~x+1定数范围
                        target_diff = int(difficulty)
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
                    self.ap.logger.info(f"{msgs}")
                    message_data = {
                        "group_id": str(ctx.event.launcher_id),
                        "user_id": "",
                        "messages": [
                            {
                                "type": "node",
                                "data": {
                                    "user_id": "2537971097",
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
                            {"text": f"波师：你总是这样"},
                            {"text": f"波师：[图片]"},
                            {"text": f"波师：我们还是分手吧"}
                        ],
                        "prompt": "[文件]年度学习资料.zip",
                        "summary": "点击浏览",
                        "source": "定数表"
                    }
                    await self.forward_message.send(message_data)
                case "chu容错 [歌曲id/别名] [难度]":
                    songs = []  # 歌曲列表
                    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.getenv("SONG_PATH")), "r", encoding="utf-8") as file:
                        songs = json.load(file).get("songs")
                    song = None # 目标歌曲
                    
                    song_name = re.search(r"^chu容错 (c\d+|[^ ]+)(?: (exp|mas|ult))?$", msg).group(1)
                    difficulty = re.search(r"^chu容错 (c\d+|[^ ]+)(?: (exp|mas|ult))?$", msg).group(2)
                    if difficulty == None:
                        difficulty = "mas"
                        
                    self.ap.logger.info(f"chu容错查歌：{song_name} - {difficulty}")
                    matched_songs = await self.searchSong(ctx, song_name) # 匹配歌曲列表
                    
                    if len(matched_songs) == 1:   # 只有一个符合直接返回
                        song_index = int(matched_songs[0].get('id'))
                        song = songs[song_index]
                    elif len(matched_songs) == 0:
                        await ctx.reply(MessageChain([Plain(f"没有找到{song_name}，请尝试输入歌曲全称或其他别名")]))
                        return
                    else:
                        msg_chain = MessageChain([Plain(f"有多个曲目符合条件\n")])
                        for song in matched_songs:
                            msg_chain.append(Plain(f"c{song.get('id')} - {song.get('songId')}\n"))
                        msg_chain.append(Plain(f"\n请使用“chu容错 [歌曲ID]”进行容错计算"))
                        await ctx.reply(msg_chain)
                        return
                    # 难度选择
                    try:
                        if self.diff2index[difficulty] == 4 and len(song['sheets']) < 5: # 检查是否有Ultima难度
                            await ctx.reply(MessageChain([Plain(f"歌曲{song_name}无Ultima难度")]))
                            return
                    except Exception as e:
                        await ctx.reply(MessageChain([Plain(f"未知难度")]))
                        return
                    tolerance = self.calcTolerance(song['sheets'][self.diff2index[difficulty]]['noteCounts'])
                    self.ap.logger.info(f"容错：{tolerance}")
                    await ctx.reply(MessageChain([
                        Plain(f"歌曲 - {song.get("songId")} - {difficulty}难度容错：\n"),
                        Plain(f"鸟容错\n100小j：{tolerance["1007500"]["100j"]}个attack\n50小j：{tolerance["1007500"]["50j"]}个attack\n"),
                        Plain(f"鸟加容错\n100小j：{tolerance["1009000"]["100j"]}个attack\n50小j：{tolerance["1009000"]["50j"]}个attack")
                    ]))
                    return
                case "chuchart [歌曲id/别名] [难度]":
                    song = None # 目标歌曲
                    songs = []  # 歌曲列表
                    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.getenv("SONG_PATH")), "r", encoding="utf-8") as file:
                        songs = json.load(file).get("songs")
                    song_name = re.search(r"^chuchart (c\d+|.+?)(?: (exp|mas|ult))?$", msg).group(1)
                    difficulty = re.search(r"^chuchart (c\d+|.+?)(?: (exp|mas|ult))?$", msg).group(2)
                    if difficulty == None:
                        difficulty = "mas"
                        
                    self.ap.logger.info(f"chuchart查歌：{song_name} - {difficulty}")
                    matched_songs = await self.searchSong(ctx, song_name)
                    
                    if len(matched_songs) == 1:   # 只有一个符合直接返回
                        song_index = int(matched_songs[0].get('id'))
                        song = songs[song_index]
                    elif len(matched_songs) == 0:
                        await ctx.reply(MessageChain([Plain(f"没有找到{song_name}，请尝试输入歌曲全称或其他别名")]))
                        return
                    else:
                        msg_chain = MessageChain([Plain(f"有多个曲目符合条件\n")])
                        for song in matched_songs:
                            msg_chain.append(Plain(f"c{song.get('id')} - {song.get('songId')}\n"))
                        msg_chain.append(Plain(f"\n请使用“chu容错 [歌曲ID]”进行容错计算"))
                        await ctx.reply(msg_chain)
                        return
                    # 难度选择
                    try:
                        if self.diff2index[difficulty] == 4 and len(song['sheets']) < 5: # 检查是否有Ultima难度
                            await ctx.reply(MessageChain([Plain(f"歌曲{song_name}无Ultima难度")]))
                            return
                    except Exception as e:
                        await ctx.reply(MessageChain([Plain(f"未知难度")]))
                        return
                    # cache中寻找chart
                    chartid = self.getChartID(song)
                    if self.checkChartCache(chartid, difficulty):
                        local_path = os.path.join(chart_cache_dir, f"{chartid}_{"" if difficulty == "mas" else difficulty}.png")
                        self.ap.logger.info(f"命中缓存，使用本地图片")
                        img_conponent = await image_langbot.from_local(local_path)
                        await ctx.reply(MessageChain([
                            Plain(f"歌曲 - {song.get('songId')}\n"),
                            Plain(f"难度 - {difficulty}\n"),
                            Plain(f"Artist - {song.get('artist')}\n"),
                            Plain(f"NoteDesigner - {song.get('sheets')[self.diff2index[difficulty]]['noteDesigner']}\n"),
                            Plain(f"BPM - {song.get('bpm')}\n"),
                            Plain(f"Notes - {song.get('sheets')[self.diff2index[difficulty]]['noteCounts']['total']}"),
                            img_conponent
                        ]))
                        return
                    self.ap.logger.info(f"歌曲别名匹配：{song['songId']} -> {chartid}")
                    chartgen = self.getChartGen(chartid)
                    self.ap.logger.info(f"对应版本号：{chartgen}")
                    # 未命中请求
                    charturl, bgurl, barurl= self.concatChartUrl(chartid, chartgen, difficulty)
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
                    }
                    try:
                        response1 = requests.get(charturl, headers=headers)
                        response2 = requests.get(bgurl, headers=headers)
                        response3 = requests.get(barurl, headers=headers)
                    except Exception as e:
                        self.ap.logger.error(f"请求失败：{e}")
                        await ctx.reply(MessageChain([Plain(f"请求失败，可能是网络不好，请稍后再试")]))
                        return
                    self.ap.logger.info(f"请求完成")
                    if response1.status_code == 200 and response2.status_code == 200:
                        self.ap.logger.info(f"图片加载中")
                        img1 = PIL.Image.open(BytesIO(response1.content)).convert("RGBA")
                        img2 = PIL.Image.open(BytesIO(response2.content)).convert("RGBA")
                        img3 = PIL.Image.open(BytesIO(response3.content)).convert("RGBA")
                        self.ap.logger.info(f"图片加载完成")
                        if img1.size == img2.size and img1.size == img3.size:
                            width, height = img1.size
                            new_image = PIL.Image.new("RGBA", (width, height), color = (0, 0, 0, 255))
                            new_image = PIL.Image.alpha_composite(new_image, img2)
                            new_image = PIL.Image.alpha_composite(new_image, img1)
                            new_image = PIL.Image.alpha_composite(new_image, img3)
                            # 保存拼接后的图片
                            save_path = os.path.join(chart_cache_dir, f"{chartid}_{"" if difficulty == "mas" else difficulty}.png")
                            new_image.save(save_path)
                            img_conponent = await image_langbot.from_local(save_path)
                            self.ap.logger.info(f"发送chart中...")
                            await ctx.reply(MessageChain([
                                Plain(f"歌曲 - {song.get('songId')}\n"),
                                Plain(f"难度 - {difficulty}\n"),
                                Plain(f"Artist - {song.get('artist')}\n"),
                                Plain(f"NoteDesigner - {song.get('sheets')[self.diff2index[difficulty]]['noteDesigner']}\n"),
                                Plain(f"BPM - {song.get('bpm')}\n"),
                                Plain(f"Notes - {song.get('sheets')[self.diff2index[difficulty]]['noteCounts']['total']}"),
                                img_conponent
                            ]))
                        else:
                            self.ap.logger.info("两张图片尺寸不同，无法拼接！")
                case _:
                    pass
                        
    # 插件卸载时触发
    def __del__(self):
        pass
