import os
import os.path as osp
import json
import random
import dotenv
import sqlite3
import numpy as np
from jinja2 import Template
import base64

from pkg.plugin.context import EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import *

from .query_song import searchSong
from .utils.songutil import *
from .utils.apicaller import *

dotenv.load_dotenv()
SONGS_PATH = os.path.join(os.path.dirname(__file__), "..", os.getenv("SONG_PATH"))
COVER_CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'cache', 'covers')
DB_PATH = os.path.join(os.path.dirname(__file__), "..", 'data', 'data.db')
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", 'template', 'best.html')
BEST_HTML_DIR = os.path.join(os.path.dirname(__file__), "..", 'cache', 'best')

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

def format_with_commas(number: int):
    return f"{number:,}"

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

def renderCardHTML(records: list[tuple]):
    '''生成B30图表HTML'''
    html = []
    # row_open = False
    html = ['<div class="card-container">']
    for index, record in enumerate(records):
        # [cid, score, difficulty, name, const, rating, cover]
        # 处理背景色 background-color: rgb(123, 7, 195);
        background_color = "rgb(123, 7, 195)"
        match str(record[2]):
            case "basic":
                background_color = "#10D472)"
            case "advanced":
                background_color = "#D9EB3A"
            case "expert":
                background_color = "#FF0000"
            case "master":
                background_color = "#8C00FF"
            case "ultima":
                background_color = "#000000"
            case _:
                background_color = "#8C00FF"
        # 处理cover
        songutil = SongUtil()
        songutil.checkIsHit(os.getenv('COVER_URL'), record[-1])
        card_html = f"""
        <div class="card">
            <div class="song_cover">
                <img src="{os.path.join(COVER_CACHE_DIR, record[-1] + ".webp")}" alt="">
            </div>
            <div class="upper" style="background-color: {background_color};">
                <div class="sequence"><p>#{index+1}</p></div>
                <div class="song_data">
                    <div class="song_stats">
                        <p class="song_name">{record[3]}</p>
                        <p class="song_score">{format_with_commas(int(record[1]))}</p>
                        <div class="song_diff_const_rt">
                            <div class="song_diff_const">
                                <p class="song_diff">{record[2][0].upper()+record[2][1:]}</p>
                                <p class="song_const">{record[-3]}</p>
                            </div>
                            <div>
                                <p class="song_rt">Rating: {record[-2]}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="lower">
                <div class="extra">
                    <div class="clear_status">CLEAR</div>
                    <div class="rank">{getRank(int(record[1]))}</div>
                </div>
            </div>
        </div>
        """
        html.append(card_html)

    # if row_open:
    #     html.append("</tr>")
    html.append('</div>')
    return "\n".join(html)

def renderBestHTML(card_html: str, best30: float, username: str="CHUNITHMCHUNITHMCHUNITHM", avatar: str=None):
    '''渲染Best30HTML'''
    with open(TEMPLATE_PATH, 'r', encoding='utf-8'):
        template = Template(open(TEMPLATE_PATH, 'r', encoding='utf-8').read())
    bg_image = osp.join(osp.dirname(__file__), "..", "images", "best_bg.webp")
    with open(bg_image, 'rb') as f:
        encoded_bg = base64.b64encode(f.read()).decode()
    html = template.render(
        cards=card_html, 
        b30=best30, 
        username=username, 
        avatar=osp.join(osp.dirname(__file__), "..", "images", "default_avatar.png"),
        bg_image=encoded_bg
    )
    ### DEBUG
    with open(f"best_{username}.html", 'w', encoding='utf-8') as f:
        f.write(html)
    return html

async def convertHTMLtoIMG(html: str, output_path: str, width=2230, height=720, wait_until='networkidle'):
    '''HTML转图片'''
    def embed_local_images(html_str: str) -> str:
        """
        将 HTML 中 <img src="本地路径"> 转为 base64 内嵌
        """
        import base64
        def repl(match):
            src = match.group(1)
            path = Path(src)
            if path.exists() and path.is_file():
                # 读取文件并转 base64
                mime_type = 'image/png'
                if src.lower().endswith('.webp'):
                    mime_type = 'image/webp'
                elif src.lower().endswith('.jpg') or src.lower().endswith('.jpeg'):
                    mime_type = 'image/jpeg'
                elif src.lower().endswith('.gif'):
                    mime_type = 'image/gif'
                with path.open('rb') as f:
                    b64 = base64.b64encode(f.read()).decode()
                return f'src="data:{mime_type};base64,{b64}"'
            return match.group(0)

        return re.sub(r'src=["\'](.*?)["\']', repl, html_str)
    
    html = embed_local_images(html)
    
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': width, 'height': height})
        await page.set_content(html, wait_until=wait_until)
        await page.screenshot(path=output_path, full_page=True)
        await browser.close()

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
        average_rating = round(average_rating, 3)
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
                        "user_id": user_id,
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
            # 增加cover列
            cover = []
            with open(SONGS_PATH, 'r', encoding='utf-8-sig') as f:
                songs = json.load(f)
                for cid in sorted_records[:, 0]:
                    for song in songs:
                        if song.get('idx') == str(cid)[1:]:
                            cover.append(song.get('img'))
                            break
            try:
                # [cid, score, difficulty, name, const, rating] -> [cid, score, difficulty, name, const, rating, cover]
                sorted_records = np.concatenate((sorted_records, np.array(cover).reshape(-1, 1)), axis=1)
            except Exception as e:
                await ctx.reply(MessageChain([Plain(f"拼接失败，{e}")]))
            try:
                card_html = renderCardHTML(sorted_records.tolist())
                html = renderBestHTML(card_html, average_rating)
                img_path = osp.join(BEST_HTML_DIR, f"best_{user_id}.png")
                await convertHTMLtoIMG(html, img_path)
                img_component = await Image.from_local(img_path)
                await ctx.reply(MessageChain([img_component]))
            except Exception as e:
                # await ctx.reply(MessageChain([Plain(f"traceback: {traceback.format_exc()}")]))
                await ctx.reply(MessageChain([Plain(f"生成Best30图表失败，{e}")]))
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
    
    
    
    