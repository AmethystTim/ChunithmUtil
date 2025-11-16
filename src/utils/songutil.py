import json
import os
import re
import requests

class SongUtil:
    def __init__(self):
        self.diff2index = {
            "basic": 0,
            "advanced": 1,
            "expert": 2,
            "master": 3,
            "ultima": 4,
        }
        self.alias4diff = {
            "basic": ["bas", "bsc"],
            "advanced": ["adv"],
            "expert": ["exp", "exprt"],
            "master": ["mas", "mst"],
            "ultima": ["ult"],
        }
    
    def getDiff2Index(self, difficulty: str) -> int:
        '''获取难度对应的索引
        
        Args:
            difficulty (str): 难度
        
        Returns:
            难度对应的索引
        '''
        if self.diff2index.get(difficulty.lower()):
            return self.diff2index[difficulty.lower()]
        else:
            for keys in self.alias4diff.keys():
                for alias in self.alias4diff[keys]:
                    if alias == difficulty.lower():
                        return self.diff2index[keys]
        return None
    
    def getIndex2Diff(self, index: int) -> str:
        '''获取索引对应的难度
        
        Args:
            index (int): 索引
        
        Returns:
            索引对应的难度
        '''
        for keys in self.diff2index.keys():
            if self.diff2index[keys] == index:
                return keys
        return None
    
    def getArtists(self, songs: list) -> str:
        '''获取所有曲师构成的列表
        
        Args:
            songs (list): 歌曲列表
        
        Returns:
            曲师列表
        '''
        return list(set([song.get('artist') for song in songs]))
    
    # def getNoteDesigners(self, songs: list) -> str:
    #     '''获取所有谱师构成的列表
        
    #     Args:
    #         songs (list): 歌曲列表
        
    #     Returns:
    #         谱师列表
    #     '''
    #     return list(set([diff.get('noteDesigner') for song in songs for diff in song.get('sheets')]))
    
    def getSongsByArtist(self, artist: str, songs: list) -> list:
        '''获取指定曲师的歌曲列表
        
        Args:
            artist (str): 歌曲曲师
            songs (list): 歌曲列表
        
        Returns:
            曲师的歌曲列表
        '''
        songs_by_artist = []
        for song in songs:
            if song.get('artist') == artist:
                songs_by_artist.append(song)
        return list(set(songs_by_artist))
    
    # def getSheetsByNoteDesigner(self, note_designer: str, songs: list) -> dict:
    #     '''获取指定谱师的作品列表
        
    #     Args:
    #         note_designer (str): 谱师
    #         songs (list): 歌曲列表
        
    #     Returns:
    #         谱师的作品列表
    #     '''
    #     sheets_by_note_designer = {}
    #     for song in songs:
    #         for sheet in song.get('sheets'):
    #             if sheet.get('noteDesigner') != note_designer:
    #                 continue
    #             if song.get('songId') not in sheets_by_note_designer.keys():
    #                 sheets_by_note_designer[song.get('songId')] = [
    #                         sheet.get('difficulty')
    #                     ]
    #             else:
    #                 sheets_by_note_designer[song.get('songId')].append(sheet.get('difficulty'))
    #     return sheets_by_note_designer 

    def checkIsHit(self, coverUrl: str, imageName: str, extension: str=".webp") -> None:
        '''检查是否缓存曲绘
        
        Args:
            coverUrl (str): 图片链接
            imageName (str): 图片名称
            extension (str, optional): 图片扩展名. Defaults to ".webp".
        Returns:
            None: 无返回值
        '''
        COVER_CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'cache', 'covers')
        complete_filename = imageName + extension
        if os.path.exists(os.path.join(COVER_CACHE_DIR, complete_filename)):
            return
        else:
            response = requests.get(coverUrl + complete_filename)
            if response.status_code == 200:
                with open(os.path.join(COVER_CACHE_DIR, complete_filename), 'wb') as f:
                    f.write(response.content)
            return
    
    def calcTolerance(self, song: dict, difficulty: str) -> dict:
        '''计算指定难度的容错率
        
        Args:
            song (dict): 歌曲信息
            difficulty (str): 难度
        
        Returns:
            容错信息
        '''
        index = self.getDiff2Index(difficulty)
        if index is None:
            return None
        total_score = 10_10000  # 理论值分数
        total_notes = song.get('notes')
        justice_loss = 0.01 * (total_score / total_notes)    # 小J损失分数
        attack_loss = (50/101) * (total_score / total_notes)    # attack损失分数
        # 鸟容错计算
        _7500_loss = 2500 
        _7500_max_attack_num = _7500_loss // attack_loss
        _7500_max_justice_num = _7500_loss % attack_loss // justice_loss

        # 鸟加容错
        _9000_loss = 1000
        _9000_max_attack_num = _9000_loss // attack_loss
        _9000_max_justice_num = _9000_loss % attack_loss // justice_loss
        return dict({
            "1007500": {
                "attack": int(_7500_max_attack_num),
                "justice": int(_7500_max_justice_num),
            },
            "1009000": {
                "attack": int(_9000_max_attack_num),
                "justice": int(_9000_max_justice_num),
            }
        })    
        
    def addAlias(self, cid: str, alias_for_songs: dict, aliases_to_add: list) -> tuple[list, list]:
        '''添加歌曲别名
        
        Args:
            cid (str): 歌曲ID
            alias_for_songs (dict): alias.json的songs字段
            aliases_to_add (list): 要添加的别名列表
        Returns:
            (available_aliases, unavailable_aliases): 别名添加成功列表和失败列表
        '''
        available_aliases = []      # 别名添加成功列表
        unavailable_aliases = []    # 别名添加失败列表
        aliases_to_add = list(set(aliases_to_add))
        NEW_ALIAS_PATH = os.path.join(os.path.dirname(__file__), '..', '..', os.getenv("ALIAS_PATH"))
        for song_aliases in alias_for_songs:
            print(f"song_aliases is {song_aliases}")
            if song_aliases.get('cid') == cid:
                for alias in aliases_to_add:
                    alias = alias.strip()
                    if alias == "" or alias == " ":
                        continue
                    if re.match(r"^c\d+$", alias):
                        continue
                    if not alias in song_aliases.get('aliases'):
                        song_aliases.get('aliases').append(alias)
                        available_aliases.append(alias)
                    else:
                        unavailable_aliases.append(alias)
                with open(NEW_ALIAS_PATH, "w", encoding="utf-8") as file:
                    json.dump({"songs": alias_for_songs}, file, indent=4, ensure_ascii=False)
                return available_aliases, unavailable_aliases
                
        # 歌曲ID不存在，创建新歌曲别名列表
        song_aliases = {"cid": cid, "aliases":[]}
        available_aliases = []
        unavailable_aliases = []
        for alias in aliases_to_add:
            if not alias in song_aliases.get('aliases'): 
                song_aliases.get('aliases').append(alias)
                available_aliases.append(alias)
            else:
                unavailable_aliases.append(alias)
        alias_for_songs.append(song_aliases)
        
        with open(NEW_ALIAS_PATH, "w", encoding="utf-8") as file:
            json.dump({"songs": alias_for_songs}, file, indent=4, ensure_ascii=False)
        return available_aliases, unavailable_aliases

    def getAlias(self, cid: str, alias_json_songs: list) -> list:
        '''获取歌曲别名
        
        Args:
            cid: 歌曲ID
            alias_json_songs: alias.json的songs字段
        
        Returns:
            aliases: 歌曲别名列表
        '''
        aliases = []
        for song in alias_json_songs:
            if song.get('cid') == cid:
                aliases = song.get('aliases')
                return aliases
        return aliases
    
    def delAlias(self):
        pass