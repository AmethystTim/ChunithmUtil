import os
import requests
import PIL
from io import BytesIO

from .searcher import *

class ChartUtil:
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
    
    def getChartGen(self, chartID: str) -> str:
        '''获取谱面版本ID
        
        Args:
            chartID: 谱面ID
        Returns:
            谱面版本ID
        '''
        ID2GEN_PATH = os.path.join(os.path.dirname(__file__), '..', '..', os.getenv("ID2GEN_PATH"))
        with open(ID2GEN_PATH, "r", encoding="utf-8") as f:
            f = json.load(f)
            return f.get(chartID) 
        
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
    
    def checkIsHit(self, chartid, difficulty) -> None:
        '''判断是否缓存谱面
        
        Args:
            chartid: 谱面ID
            difficulty: 难度
        Returns:
            None: 无返回值
        '''
        CHART_CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'cache', 'charts')
        if os.path.exists(os.path.join(CHART_CACHE_DIR, f'{chartid}_{"" if difficulty == "mas" else difficulty}.png')):
            return

        chartgen = self.getChartGen(chartid)
        urls = self.getChartUrl(chartid, chartgen, difficulty)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
        }
        responses = []
        try:
            for url in urls:
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    responses.append(response)
                else:
                    print(f"[ChunithmUtil] 请求失败：{response.status_code} {url}")
        except Exception as e:
            print(f"请求失败：{e}")
            return
        
        if all(res.status_code == 200 for res in responses):
            imgs = []
            for res in responses:
                img = PIL.Image.open(BytesIO(res.content)).convert("RGBA")
                imgs.append(img)
            img1, img2, img3 = imgs
            if img1.size == img2.size and img1.size == img3.size:
                width, height = img1.size
                new_image = PIL.Image.new("RGBA", (width, height), color = (0, 0, 0, 255))
                new_image = PIL.Image.alpha_composite(new_image, img2)
                new_image = PIL.Image.alpha_composite(new_image, img1)
                new_image = PIL.Image.alpha_composite(new_image, img3)
                
                save_path = os.path.join(CHART_CACHE_DIR, f'{chartid}_{"" if difficulty == "mas" else difficulty}.png')
                new_image.save(save_path)
            else:
                print("[ChunithmUtil] 两张图片尺寸不同，无法拼接！")