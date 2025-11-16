import os
import aiohttp
import PIL
import dotenv
import traceback
import base64
import ssl
import certifi
import aiofiles
import asyncio
import httpx

from .searcher import *
from .apicaller import *
from .songutil import *

CHART_CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'cache', 'charts')

ssl_context = ssl.create_default_context(cafile=certifi.where())

dotenv.load_dotenv()

ROMAJI_2_JP = {
    "uso": "嘘",
    "wari": "割",
    "shou": "翔",
    "kura": "蔵",
    "kyou": "狂",
    "kai": "改",
    "geki": "撃",
    "modo": "戻",   # 这里原始是 modo / mdo? 数据里有 "modo"
    "ban": "半",
    "toki": "時",
    "soku": "速",
    "tome": "止",
    "mai": "舞",
    "nuno": "布",
    "haya": "速",    # 速 (早い)
    "dan": "弾",
    "hi": "避",
    "hika": "光",
    "sake": "避",
    "hane": "跳",
    "uta": "歌",
    "han": "半",
    "nazo": "？",
    "!": "！",
    "q": "？",       # 数据里 star_q → ？
}

class WEChartUtil:
    def __init__(self):
        pass
    
    def getChartID(self, song: dict) -> str:
        '''获取谱面ID
        
        Args:
            song: 歌曲字典
        Returns:
            谱面ID
        '''
        ID2NAME_PATH = os.path.join(os.path.dirname(__file__), '..', '..', os.getenv("ID2NAME_PATH"))
        with open(ID2NAME_PATH, "r", encoding="utf-8") as f:
            f = json.load(f)
            searcher = Searcher()
            res = searcher.generalFuzzySearch(song['songId'], list(f.values()))
            if len(res) > 0:
                id = list(f.keys())[list(f.values()).index(res[0])]
                return id
        return None
    
    def extractDiff(self, rawDiff: str):
        '''
        提取难度
        paradise_uso3 -> 3
        '''
        return re.findall(r'\d+', rawDiff)[-1]
    
    def extractType(self, rawType: str):
        '''
        提取类型
        paradise_uso3 -> uso
        '''
        type = re.findall(r'[^0-9]+', rawType)[-1]
    
    def getWEDifficulty(self, chartid: str, type: str):
        '''获取谱面难度
        
        Args:
            chartid: 谱面ID
            type: 类别
        Returns:
            谱面难度
        '''
        ID2DIFF_PATH = os.path.join(os.path.dirname(__file__), '..', '..', os.getenv("ID2DIFF_WE_PATH"))
        with open(ID2DIFF_PATH, "r", encoding="utf-8") as f:
            f = json.load(f)
            tmp_list = [f.get(key) for key in f.keys() if chartid == re.sub(r'end.*', '', key)]
            chart_info = self.getChartInfo(chartid)
            if chart_info:
                return chart_info['difficulty']
        return -1
    
    def getChartUrl(self, chartID: str, gen: str, diff: str = "mas") -> list:
        '''拼接谱面URL
        
        Args:
            chartID: 谱面ID
            gen: 谱面版本ID
            diff: 难度
        Returns:
            [谱面URL, 背景URL, 小节数URL]
        '''
        charturl = os.getenv("CHART_URL").replace("<chartid>", chartID)
        bgurl = os.getenv("CHART_BG_URL").replace("<chartid>", chartID)
        barurl = os.getenv("CHART_BAR_URL").replace("<chartid>", chartID)
        
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
        return [charturl, bgurl, barurl]

    async def downloadSingle(self, client, url, save_path, index):
        temp_save_path = save_path.replace('.png', f'_{index}.png')
        
        try:
            async with client.stream("GET", url, follow_redirects=True) as resp:
                if resp.status_code == 200:
                    print(f"[ChunithmUtil] 请求成功：{resp.status_code} {url}")
                    async with aiofiles.open(temp_save_path, "wb") as f:
                        async for chunk in resp.aiter_bytes():
                            await f.write(chunk)
                    print(f"[ChunithmUtil] 下载完成 {url}")
                else:
                    print(f"[ChunithmUtil] 请求失败：{resp.status_code} {url}")
        except Exception as e:
            print(f"[ChunithmUtil] 下载失败：{url} - {type(e).__name__}: {e}")
            traceback.print_exc()
    
    async def sendChart(self, file_path: str, group_id: str, song: dict, difficulty: str):
        '''使用消息平台发送谱面'''
        print("[ChunithmUtil] 使用消息平台发送谱面...")
        msgplatform = MsgPlatform(3000)
        encoded_string = ''
        if not os.path.exists(file_path):
            print(f"[ChunithmUtil] 文件不存在！ {file_path}")
            return
        async with aiofiles.open(file_path, 'rb') as image_file:
            image_binary = await image_file.read()
            encoded_string = base64.b64encode(image_binary).decode()
        response = await msgplatform.callApi('/download_file', {
            "base64": encoded_string,
            "thread_count": 0,
            "name": os.path.basename(file_path)
        })
        print(f"[ChunithmUtil] 将图片存储至temp目录 {response['data']['file']}")
        temp_path = response['data']['file']
        songutil = SongUtil()
        await msgplatform.callApi('/send_group_msg', {
            "group_id": group_id,
            "message": [
                {
                    "type": "text",
                    "data": {
                        "text": f"歌曲 - {song.get('songId')}\n难度 - {difficulty}\nArtist - {song.get('artist')}\nNoteDesigner - {song.get('sheets')[songutil.getDiff2Index(difficulty)]['noteDesigner']}\nBPM - {song.get('bpm')}\nNotes - {song.get('sheets')[songutil.getDiff2Index(difficulty)]['noteCounts']['total']}"
                    }
                },
                {
                    "type": "image",
                    "data": {
                        "file": temp_path
                    }
                }
            ]
        })
    
    async def getChart(self, chartid: str, difficulty: str, group_id: str, song: dict) -> None:
        chartgen = self.getChartGen(chartid)
        urls = self.getChartUrl(chartid, chartgen, difficulty)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
        }
        save_path = os.path.join(CHART_CACHE_DIR, f'{chartid}_{"" if difficulty == "mas" else difficulty}.png')

        async with httpx.AsyncClient(headers=headers, timeout=120, verify=False) as client:
            tasks = [
                self.downloadSingle(client, url, save_path, i)
                for i, url in enumerate(urls)
            ]
            await asyncio.gather(*tasks)

        self.processChart(save_path)
        await self.sendChart(save_path, group_id, song, difficulty)
        
    def checkIsHit(self, chartid, type) -> bool:
        '''判断是否缓存谱面
        
        Args:
            chartid: 谱面ID
            type: 类别
        Returns:
            None: 无返回值
        '''
        return os.path.exists(os.path.join(CHART_CACHE_DIR, f'we_{chartid}_{type if type else ""}.png'))
    
    def processChart(self, save_path: str) -> None:
        '''处理并保存谱面
        
        Args:
            responses_content: 响应内容列表
            save_path: 保存路径
        '''
        imgs = []
        for i in range(3):
            img_path = save_path.replace('.png', f'_{i}.png')
            if not os.path.exists(img_path):
                print(f"[ChunithmUtil] 图片不存在：{img_path}")
                return
            img = PIL.Image.open(img_path).convert("RGBA")
            imgs.append(img)
        img1, img2, img3 = imgs
        try:
            if not (img1.size == img2.size == img3.size):   # 以最小宽高为准裁剪图片
                min_width = min(img1.size[0], img2.size[0], img3.size[0])
                min_height = min(img1.size[1], img2.size[1], img3.size[1])
                img1 = img1.crop((0, 0, min_width, min_height)).resize((width, height), PIL.Image.ANTIALIAS)
                img2 = img2.crop((0, 0, min_width, min_height)).resize((width, height), PIL.Image.ANTIALIAS)
                img3 = img3.crop((0, 0, min_width, min_height)).resize((width, height), PIL.Image.ANTIALIAS)
            
            width, height = img1.size
            new_image = PIL.Image.new("RGBA", (width, height), color = (0, 0, 0, 255))
            
            new_image = PIL.Image.alpha_composite(new_image, img2)
            new_image = PIL.Image.alpha_composite(new_image, img1)
            new_image = PIL.Image.alpha_composite(new_image, img3)
            
            new_image.save(save_path)
            print("[ChunithmUtil] 铺面合成成功")
            for i in range(3):
                img_path = save_path.replace('.png', f'_{i}.png')
                if os.path.exists(img_path):
                    os.remove(img_path)
        except Exception as e:
            print(f"[ChunithmUtil] 处理谱面失败：{e}")
            traceback.print_exc()