# import os
# import os.path as osp
# import json
# import dotenv
# import sqlite3
# import numpy as np
# import requests
# import PIL

# from pkg.plugin.context import EventContext
# from pkg.plugin.events import *  # 导入事件类
# from pkg.platform.types import *

# from .query_song import searchSong
# from .utils.songutil import *

# USER_JSON_PATH = osp.join(osp.dirname(__file__), 'data', 'users.json')
# JACKET_DIR = osp.join(osp.dirname(__file__), 'data', 'jackets')
# CONST_DIR = osp.join(osp.dirname(__file__), 'data', 'cache', 'const')
# HELP_API_IMG_PATH = osp.join(osp.dirname(__file__), 'images', 'api.png')

# class GradeManager:
#     def __init__(self, ctx: EventContext, user_id: str):
#         self.ctx = ctx
#         self.user_id = user_id
#         self.consts = [
#             "9", "9+", "10", "10+", "11", "11+",
#             "12", "12+", "13", "13+", "14", "14+", "15", "15+"
#         ]
#         # 初始化session（保持会话，利于处理Cookie/会话验证）
#         self.session = requests.Session()
#         # 模拟浏览器的请求头（关键：解决反爬问题）
#         self.headers = {
#             "User-Agent": "curl/8.4.0",  # 关键：使用你本地curl的真实版本
#             "Accept": "*/*",             # curl的默认Accept头
#             # 注意：curl默认不会发送Referer、Accept-Language等头，这里也不添加，保持和curl一致
#         }
#         # 给session添加默认请求头
#         self.session.headers.update(self.headers)

#     async def readUsersJson(self):
#         users = {}
#         with open(USER_JSON_PATH, 'r') as f:
#             users = json.load(f).get('users', {})
#         return users

#     async def writeUsersJson(self, users: dict):
#         try:
#             with open(USER_JSON_PATH, 'w') as f:
#                 json.dump({'users': users}, f, indent=4)
#             return 0
#         except Exception as e:
#             await self.ctx.reply([Plain(f'写入用户信息失败：{e}')])
#             return -1

#     def checkIsBind(self, users: dict):
#         return self.user_id in users.keys()

#     async def bindAccount(self, token: str):
#         users = await self.readUsersJson()
#         # 检查是否已绑定
#         if self.checkIsBind(users):
#             await self.ctx.reply([Plain('你已经绑定过账号了，请先使用“unbind”解绑再绑定新的账号')])
#             return
#         # 绑定账号
#         users[self.user_id] = token
#         await self.writeUsersJson(users)
#         await self.ctx.reply([Plain('绑定成功，请及时撤回个人TOKEN')])

#     async def unbindAccount(self):
#         users = await self.readUsersJson()
#         # 检查是否已绑定
#         if not self.checkIsBind(users):
#             await self.ctx.reply([Plain('你还没有绑定账号，请先使用“bind [TOKEN]”绑定账号')])
#             return
#         # 解绑账号
#         del users[self.user_id]
#         await self.writeUsersJson(users)
#         await self.ctx.reply([Plain('解绑成功')])

#     def getSongs(self) -> list:
#         url = "https://maimai.lxns.net/api/v0/chunithm/song/list"
#         response = requests.get(url)
#         data = response.json()
#         songs = data.get('songs', [])
#         return songs

#     def getVersions(self) -> list:
#         url = "https://maimai.lxns.net/api/v0/chunithm/song/list"
#         response = requests.get(url)
#         data = response.json()
#         versions = data.get('versions', [])
#         return versions

#     def getRank(self, score: int) -> str:
#         if score >= 1009000:
#             return "SSS+"
#         elif score >= 1007500:
#             return "SSS"
#         elif score >= 1005000:
#             return "SS+"
#         elif score >= 1000000:
#             return "SS"
#         elif score >= 990000:
#             return "S+"
#         elif score >= 975000:
#             return "S"
#         return "S-"

#     def convertRank(self, rank: str):
#         match rank:
#             case "sssp":
#                 return "SSS+"
#             case "sss":
#                 return "SSS"
#             case "ssp":
#                 return "SS+"
#             case "ss":
#                 return "SS"
#             case "sp":
#                 return "S+"
#             case "s":
#                 return "S"
#             case _:
#                 return "S-"

#     def getCovers(self, song_ids: list):
#         base_url = "https://assets2.lxns.net/chunithm"
#         for song_id in song_ids:
#             song_cover_path = osp.join(JACKET_DIR, f"{song_id}.png")
#             try:
#                 # 检查本地文件是否完好
#                 if osp.exists(song_cover_path):
#                     try:
#                         with PIL.Image.open(song_cover_path) as img:
#                             img.verify()
#                         continue
#                     except (IOError, SyntaxError) as e:
#                         print(f"曲绘{song_id}.png损坏：{e}，将重新下载")

#                 # 发送请求（使用session，带浏览器请求头，添加超时）
#                 endpoint = f"/jacket/{song_id}.png"
#                 response = self.session.get(
#                     base_url + endpoint,
#                     timeout=(5, 10),
#                     # 禁用重定向（可选：若服务器重定向到验证页，可提前发现）
#                     # allow_redirects=False
#                 )

#                 # 第一步：检查状态码
#                 if response.status_code != 200:
#                     print(f"曲绘{song_id}.png请求失败，状态码：{response.status_code}")
#                     continue

#                 # 第二步：检查内容类型（过滤HTML/JS）
#                 content_type = response.headers.get('Content-Type', '')
#                 if 'image' not in content_type:
#                     # 打印前100个字符，便于排查返回的内容
#                     print(f"曲绘{song_id}.png返回非图片（类型：{content_type}），内容预览：{response.text[:100]}")
#                     # 可选：将错误内容保存，便于分析反爬机制
#                     # with open(f"{song_id}_error.html", 'w', encoding='utf-8') as f:
#                     #     f.write(response.text)
#                     continue

#                 # 第三步：写入文件
#                 try:
#                     with open(song_cover_path, 'wb') as f:
#                         f.write(response.content)
#                     print(f"曲绘{song_id}.png下载并写入成功")
#                 except (PermissionError, OSError) as e:
#                     print(f"写入曲绘{song_id}.png失败：{e}")

#             except requests.exceptions.RequestException as e:
#                 print(f"曲绘{song_id}.png网络请求出错：{e}")
#             except Exception as e:
#                 print(f"处理曲绘{song_id}.png时发生未知错误：{e}")

#     def getRankStatistcs(self, data: list):
#         sssp = f"SSS+ {len([song for song in data if song.get('score') >= 1009000])}"
#         sss = f"SSS {len([song for song in data if song.get('score') >= 1007500 and song.get('score') < 1009000])}"
#         ssp = f"SS+ {len([song for song in data if song.get('score') >= 1005000 and song.get('score') < 1007500])}"
#         ss = f"SS {len([song for song in data if song.get('score') >= 1000000 and song.get('score') < 1005000])}"
#         sp = f"S+ {len([song for song in data if song.get('score') >= 990000 and song.get('score') < 1000000])}"
#         s = f"S {len([song for song in data if song.get('score') >= 975000 and song.get('score') < 990000])}"
#         sm = f"S- {len([song for song in data if song.get('score') < 975000])}"
#         fc = f"FC {len([song for song in data if song.get('full_combo') == 'fullcombo'])}"
#         aj = f"AJ {len([song for song in data if song.get('full_combo') == 'alljustice'])}"
#         return f"Total {len(data)} | {sssp} | {sss} | {ssp} | {ss} | {sp} | {s} | {sm} | {fc} | {aj}"

#     def getRankColor(self, rank: str):
#         rank = rank.upper()
#         if "SSS+" in rank:
#             return (255, 255, 204, 255) # 铂金
#         elif "SSS" in rank:
#             return (255, 223, 100, 255) # 金黄
#         elif "SS+" in rank:
#             return (200, 230, 255, 255) # 淡蓝
#         elif "SS" in rank:
#             return (200, 230, 255, 255)
#         else:
#             return (221, 221, 221, 255) # 淡灰

#     def getFCAJ(self, full_combo: str):
#         if full_combo == 'fullcombo':
#             return "FC"
#         elif full_combo == 'alljustice':
#             return "AJ"
#         else:
#             return ""

#     def drawImg(self, data: list, header: str, user_id: str, mode: str):
#         level_groups = {}
#         for song in data:
#             level_value = str(song.get('level_value'))
#             if level_value not in level_groups.keys():
#                 level_groups[level_value] = []
#             level_groups[level_value].append(song)

#         # 根据得分降序排序
#         for level_value in level_groups.keys():
#             level_groups[level_value] = sorted(level_groups[level_value], key=lambda x: x.get('score'), reverse=True)

#         # 获取曲绘
#         self.getCovers([song.get('id') for song in data])

#         # Drawing settings

#         NUM_PER_ROW = 12

#         header_font = PIL.ImageFont.truetype(osp.join(osp.dirname(__file__), 'assets', 'font', 'SJ-Narrow-Bold-2.ttf'), 72)
#         font = PIL.ImageFont.truetype(osp.join(osp.dirname(__file__), 'assets', 'font', 'sjnarrow.ttf'), 38)
#         small_font = PIL.ImageFont.truetype(osp.join(osp.dirname(__file__), 'assets', 'font', 'simhei.ttf'), 28)
#         very_small_font = PIL.ImageFont.truetype(osp.join(osp.dirname(__file__), 'assets', 'font', 'simhei.ttf'), 20)

#         levels_sorted = sorted(level_groups.keys(), reverse=True)
#         row_height = 100
#         margin = 20
#         img_width = NUM_PER_ROW * 100 + (NUM_PER_ROW + 1) * margin
#         img_height = int(len(levels_sorted) * (row_height * 3) +
#                          sum([len(songs) // NUM_PER_ROW for songs in level_groups.values()]) * (row_height * 2) +
#                          3* row_height
#                          )

#         canvas = PIL.Image.new("RGBA", (img_width, img_height), (255, 255, 255, 0))
#         draw = PIL.ImageDraw.Draw(canvas)

#         # Draw each level block
#         y = 0
#         # 大标题
#         draw.text((margin, y), f"CHUNITHM {mode.upper()} {header.upper()}", font=header_font, fill="black")
#         y += row_height
#         for level in levels_sorted:
#             songs = level_groups[level]

#             # 解析等级和rank统计内容
#             level_text = f"[ {float(level if not level == 'None' else 0.0):.1f} ]"
#             stats_text = self.getRankStatistcs(songs)

#             level_box_size = draw.textbbox((0, 0), level_text, font=font)
#             stats_box_size = draw.textbbox((0, 0), stats_text, font=font)

#             level_text_width = level_box_size[2] - level_box_size[0]
#             level_text_height = level_box_size[3] - level_box_size[1]

#             stats_text_width = stats_box_size[2] - stats_box_size[0]
#             stats_text_height = stats_box_size[3] - stats_box_size[1]

#             stats_height = max(level_text_height, stats_text_height) + 20  # 文字高度 + 内边距
#             box_padding_x = 20

#             # 第一个色块：[等级定数]
#             draw.rounded_rectangle(
#                 [(margin, y), (margin + level_text_width + box_padding_x * 2, y + stats_height + margin // 2)],
#                 radius=16,
#                 fill=(255, 255, 204, 255)
#             )
#             draw.text(
#                 (margin + box_padding_x, y + 10),
#                 level_text,
#                 font=font,
#                 fill="black"
#             )

#             # 第二个色块：[rank统计]

#             # 拆分 rank 统计和 FC/AJ
#             rank_stats_text = " | ".join(stats_text.split(" | ")[1:8])  # SSS+ ~ S-
#             extra_stats_text = " | ".join(stats_text.split(" | ")[8:])  # FC 和 AJ

#             # rank 色块
#             rank_stats_box_size = draw.textbbox((0, 0), rank_stats_text, font=font)
#             rank_stats_width = rank_stats_box_size[2] - rank_stats_box_size[0]
#             rank_stats_x = margin + level_text_width + box_padding_x * 2 + margin

#             draw.rounded_rectangle(
#                 [(rank_stats_x, y), (rank_stats_x + rank_stats_width + box_padding_x * 2, y + stats_height + margin // 2)],
#                 radius=16,
#                 fill=(220, 235, 250, 255)  # 淡蓝色
#             )
#             draw.text(
#                 (rank_stats_x + box_padding_x, y + 10),
#                 rank_stats_text,
#                 font=font,
#                 fill="black"
#             )

#             # FC/AJ 色块
#             extra_stats_box_size = draw.textbbox((0, 0), extra_stats_text, font=font)
#             extra_stats_width = extra_stats_box_size[2] - extra_stats_box_size[0]
#             extra_stats_x = rank_stats_x + rank_stats_width + box_padding_x * 2 + margin

#             draw.rounded_rectangle(
#                 [(extra_stats_x, y), (extra_stats_x + extra_stats_width + box_padding_x * 2, y + stats_height + margin // 2)],
#                 radius=16,
#                 fill=(255, 255, 204, 255)  # 铂金
#             )
#             draw.text(
#                 (extra_stats_x + box_padding_x + 2, y + 10),
#                 extra_stats_text,
#                 font=font,
#                 fill="black"
#             )

#             # 更新 y
#             y += stats_height + int(row_height * 0.5)

#             # 绘制歌曲列表
#             for i, song in enumerate(songs):
#                 x = margin + (i % NUM_PER_ROW) * (100 + margin)
#                 row_offset = (i // NUM_PER_ROW) * (row_height * 2)
#                 box_y = y + row_offset

#                 padding = 6
#                 score_font_height = 28
#                 rank_font_height = 24

#                 # 绘制整体色块背景（封面+分数+评级）
#                 total_height = 100 + score_font_height + rank_font_height
#                 rank = f'(#{i+1})' + str(self.getRank(song['score']))
#                 color = self.getRankColor(rank)

#                 draw.rounded_rectangle(
#                     [(x - padding, box_y - padding), (x + 100 + padding, box_y + total_height + padding)],
#                     radius=12,
#                     fill=color
#                 )

#                 # 曲绘
#                 try:
#                     song_cover = PIL.Image.open(osp.join(JACKET_DIR, f"{song.get('id')}.png")).resize((100, 100))
#                 except Exception as e:
#                     print(f"Failed to load cover for {song.get('id')}: {e}")
#                     # song_cover = PIL.Image.new("RGB", (100, 100), (255, 255, 255))
#                     song_cover = PIL.Image.open(osp.join(JACKET_DIR, f"notfound.jpg")).resize((100, 100))
#                 # 绘制斜条带表示难度
#                 level_index = song.get("level_index", 3)
#                 difficulty_colors = [
#                     (102, 204, 0, 220),
#                     (255, 204, 0, 220),
#                     (255, 51, 51, 220),
#                     (153, 51, 255, 220),
#                     (0, 0, 0, 220),
#                 ]
#                 band_color = difficulty_colors[level_index]
#                 band_overlay = PIL.Image.new("RGBA", (100, 100), (255, 255, 255, 0))
#                 band_draw = PIL.ImageDraw.Draw(band_overlay)
#                 band_draw.polygon([(0, 0), (30, 0), (0, 30), (0, 0)], fill=band_color)

#                 border_thickness = 1
#                 border_box = [
#                     x - border_thickness,
#                     box_y - border_thickness,
#                     x + 100 + border_thickness,
#                     box_y + 100 + border_thickness
#                 ]
#                 draw.rectangle(border_box, fill="black")

#                 canvas.paste(song_cover, (x, box_y), mask=song_cover if song_cover.mode == 'RGBA' else None)
#                 canvas.alpha_composite(band_overlay, (x, box_y))

#                 # 绘制fc/aj
#                 fullcombo = self.getFCAJ(song.get('full_combo', ''))
#                 fullcombo_colors = {
#                     'FC': (255, 223, 100, 255),
#                     'AJ': (255, 255, 204, 255)
#                 }
#                 band_color = fullcombo_colors.get(fullcombo, (0, 0, 0, 0))
#                 # band_overlay = PIL.Image.new("RGBA", (100, 100), (255, 255, 255, 0))
#                 band_draw = PIL.ImageDraw.Draw(band_overlay)
#                 band_draw.polygon([(100, 70), (100, 100), (70, 100), (100, 70)], fill=band_color)

#                 canvas.paste(song_cover, (x, box_y), mask=song_cover if song_cover.mode == 'RGBA' else None)
#                 canvas.alpha_composite(band_overlay, (x, box_y))

#                 # 分数
#                 score_str = str(song['score'])
#                 score_text_size = draw.textbbox((0, 0), score_str, font=small_font)
#                 score_text_width = score_text_size[2] - score_text_size[0]
#                 score_x = x + (100 - score_text_width) // 2
#                 score_y = box_y + 100
#                 draw.text((score_x, score_y), score_str, font=small_font, fill="black")

#                 # 评级
#                 rank = f'(#{i+1})' + str(self.getRank(song['score']))
#                 rank_text_size = draw.textbbox((0, 0), rank, font=very_small_font)
#                 rank_text_width = rank_text_size[2] - rank_text_size[0]
#                 rank_box_width = rank_text_width + 16  # 给左右边留些空

#                 rank_x = x + (100 - rank_box_width) // 2
#                 rank_y = box_y + 100 + score_font_height

#                 # 评级文字
#                 draw.text((rank_x + 8, rank_y), rank, font=very_small_font, fill="black")

#             y += ((len(songs) - 1) // NUM_PER_ROW + 1) * row_height * 2

#         bg_path = osp.join(osp.dirname(__file__), 'assets', 'bg', 'bg.webp')

#         background = PIL.Image.open(bg_path).convert('RGBA').resize(canvas.size)
#         final_image = PIL.Image.alpha_composite(background, canvas)

#         final_image = final_image.convert("RGB")
#         final_image.save(osp.join(CONST_DIR, f"{user_id}_{header}.png"))

#     async def getConst(self, const: str):
#         users = await self.readUsersJson()
#         # 检查是否已绑定
#         if not self.checkIsBind(users):
#             img = await Image.from_local(HELP_API_IMG_PATH)
#             await self.ctx.reply([
#                 Plain('你还没有绑定账号，请先使用“bind [TOKEN]”绑定账号\n\nTOKEN获取地址：https://maimai.lxns.net/user/profile'),
#                 img
#             ])
#             return
#         # 检查const是否合法
#         if not const in self.consts:
#             await self.ctx.reply([Plain('const参数不合法，请确保为const为类似以下格式：13，13+，14，14+等')])
#             return
#         # 获取const分数
#         headers = {
#             "X-User-Token": users[self.user_id],
#         }
#         # 发送请求
#         url = "https://maimai.lxns.net/api/v0/user/chunithm/player/scores"
#         response = requests.get(url, headers=headers)
#         data = response.json()
#         match data.get('code'):
#             case 200:
#                 songs_grade = data.get('data', [])
#                 target_songs = [song for song in songs_grade if song.get('level') == const]
#                 songs = self.getSongs()
#                 # 获取歌曲具体定数
#                 for song in target_songs:
#                     try:
#                         index = [s.get('id') for s in songs].index(song.get('id'))
#                         song['level_value'] = songs[index].get('difficulties')[song.get('level_index')].get('level_value')
#                     except Exception as e:
#                         print(e)
#                 self.drawImg(target_songs, const, self.user_id, "const")
#                 const_path = osp.join(CONST_DIR, f"{self.user_id}_{const}.png")
#                 img = await Image.from_local(const_path)
#                 await self.ctx.reply(MessageChain([
#                     At(int(self.user_id)),
#                     img
#                 ]))
#             case _:
#                 await self.ctx.reply([Plain(f'获取失败，请检查TOKEN是否正确')])
#                 return

#     def getGenid(self, gen: str) -> int:
#         # 版本别名表
#         aliases_for_gen = {
#             "CHUNITHM": ["无印", "初代", "無印","origin"],
#             "CHUNITHM PLUS": ["初代+", "无印+", "無印+", "初代plus", "無印plus", "初代p", "無印p", "无印plus", "无印p", "originplus", "originp", "origin+"],
#             "CHUNITHM AIR": ["air"],
#             "CHUNITHM AIR PLUS": ["air+", "airplus", "airp"],
#             "CHUNITHM STAR": ["star"],
#             "CHUNITHM STAR PLUS": ["star+", "starplus", "starp"],
#             "CHUNITHM AMAZON": ["amaz", "amazon"],
#             "CHUNITHM AMAZON PLUS": ["amaz+", "amazplus", "amazp", "amazon+", "amazonplus", "amazonp"],
#             "CHUNITHM CRYSTAL": ["crystal"],
#             "CHUNITHM CRYSTAL PLUS": ["crystal+", "crystalp", "crystalplus"],
#             "CHUNITHM PARADISE": ["paradise", "para"],
#             "CHUNITHM PARADISE LOST": ["paradiselost", "plost", "paralost", "pl"],
#             "CHUNITHM NEW": ["new"],
#             "CHUNITHM NEW PLUS": ["new+", "newplus", "newp"],
#             "CHUNITHM SUN": ["sun"],
#             "CHUNITHM SUN PLUS": ["sun+", "sunplus", "sunp"],
#             "CHUNITHM LUMINOUS": ["luminous", "lmn"],
#             "CHUNITHM LUMINOUS PLUS": ["luminous+", "lmn+", "luminousplus", "lmnp"]
#         }
#         # 根据别名表查找版本
#         target_version = None
#         for ver, aliases in aliases_for_gen.items():
#             if gen.lower() in aliases:
#                 target_version = ver
#                 break
#         versions = self.getVersions()
#         res = [ver for ver in versions if ver.get('title') == target_version]
#         return res[0].get('version') if res else None

#     async def getProg(self, gen: str, type: str) -> None:
#         '''查询版本牌子进度

#         Args:
#             gen (str): 版本名称，如：'CHUNITHM SUN'
#             type (str): 牌子名称，如：'sss

#         Returns:
#             None
#         '''
#         users = await self.readUsersJson()
#         # 检查是否已绑定
#         if not self.checkIsBind(users):
#             img = await Image.from_local(HELP_API_IMG_PATH)
#             await self.ctx.reply([
#                 Plain('你还没有绑定账号，请先使用“bind [TOKEN]”绑定账号\n\nTOKEN获取地址：https://maimai.lxns.net/user/profile'),
#                 img
#             ])
#             return
#         # 获取用户信息
#         headers = {
#             "X-User-Token": users[self.user_id],
#         }
#         # 发送请求
#         url = "https://maimai.lxns.net/api/v0/user/chunithm/player/scores"
#         response = requests.get(url, headers=headers)
#         data = response.json()
#         match data.get('code'):
#             case 200:
#                 songs_grade = data.get('data', [])
#                 songs = self.getSongs()
#                 # 获取版本id
#                 genid = self.getGenid(gen)
#                 if not genid:
#                     await self.ctx.reply([Plain(f'版本名称不正确，请检查输入')])
#                     return
#                 # 筛选指定版本的所有歌曲
#                 target_songs = [song for song in songs if song.get('version') == genid]
#                 # 添加成绩信息
#                 for song in target_songs:
#                     songs_grade_ids = [song_grade.get('id') for song_grade in songs_grade]
#                     if song.get('id') in songs_grade_ids:
#                         # 获取所有index
#                         indexes = [i for i, s in enumerate(songs_grade) if s.get('id') == song.get('id')]
#                         for index in indexes:
#                             song['difficulties'][songs_grade[index].get('level_index')]['score'] = songs_grade[index].get('score')
#                             song['difficulties'][songs_grade[index].get('level_index')]['full_combo'] = songs_grade[index].get('full_combo')

#                 # 根据difficulties拆分，只保留mas(index=3)和ult(index=4，如果有)
#                 splitted_target_songs = []
#                 for song in target_songs:
#                     if len(song.get('difficulties')) < 4:
#                         continue
#                     splitted_target_songs.append({
#                         'id': song.get('id'),
#                         'score': song.get('difficulties')[3].get('score', 0),
#                         'level_value': song.get('difficulties')[3].get('level_value', 0),
#                         'full_combo': song.get('difficulties')[3].get('full_combo'),
#                         'level_index': 3
#                     })
#                     # Ultima难度不计入
#                     # if len(song.get('difficulties')) > 4:
#                     #     splitted_target_songs.append({
#                     #         'id': song.get('id'),
#                     #         'score': song.get('difficulties')[4].get('score', 0),
#                     #         'level_value': song.get('difficulties')[4].get('level_value', 0),
#                     #         'full_combo': song.get('difficulties')[4].get('full_combo'),
#                     #         'level_index': 4
#                     #     })
#                 self.drawImg(splitted_target_songs, gen, self.user_id, "prog")
#                 const_path = osp.join(CONST_DIR, f"{self.user_id}_{gen}.png")
#                 img = await Image.from_local(const_path)

#                 achievement, stats = None, None
#                 type = type if type else 'sss'
#                 match type:
#                     case 's':
#                         achievement = 'S牌'
#                         stats = len([song for song in splitted_target_songs if song.get('score') >= 975000])
#                     case 'sss':
#                         achievement = '将'
#                         stats = len([song for song in splitted_target_songs if song.get('score') >= 1007500])
#                     case 'sss+':
#                         achievement = '全SSS+'
#                         stats = len([song for song in splitted_target_songs if song.get('score') >= 1009000])
#                     case 'aj':
#                         achievement = '神'
#                         stats = len([song for song in splitted_target_songs if song.get('full_combo') == 'alljustice'])
#                     case 'ajc':
#                         achievement = '巫'
#                         stats = len([song for song in splitted_target_songs if song.get('full_combo') == 'alljustice' and song.get('score') == 1010000])
#                     case _:
#                         achievement = '将'
#                 statistic_info = f"{gen} {achievement}进度：{stats}/{len(splitted_target_songs)}"
#                 await self.ctx.reply(MessageChain([
#                     At(int(self.user_id)),
#                     Plain('\n'),
#                     Plain(statistic_info),
#                     img
#                 ]))
#             case _:
#                 await self.ctx.reply([Plain(f'获取失败，请检查TOKEN是否正确')])
#                 return
